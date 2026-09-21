"""Discovery and the staged ingest.

Two shapes drive the design.

**The corpus grows.** Sources are found by glob and every stage is gated on
(source checksum, stage config fingerprint), so adding files costs only those
files and editing one prompt reruns only the stage that uses it.

**8 GB of VRAM.** The embedder, the vision model and the text model cannot be
resident together, so ingest runs stage-by-stage across all sources rather than
source-by-source across all stages: each model loads once per run, not once per
file. Between model stages the previous model is evicted.
"""

from __future__ import annotations

import json
import re
import time
from fnmatch import fnmatch
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from . import calendar as cal
from . import chunk as chunking
from . import extract, index, metrics, prompts
from .config import Config, Corpus
from .limits import WORK_SHA_CHARS, WORK_STEM_CHARS
from .llm import LLM
from .state import State, file_sha
from .types import Unit


@dataclass
class Source:
    path: Path
    rel: str                       # path relative to the corpus root, the stable key
    type: str
    vision: str = "auto"
    module: str | None = None
    sha: str = ""
    # Set when OCR produced a searchable copy. Later stages read this, so the
    # original under /corpus is never opened for writing.
    ocr_path: Path | None = None

    @property
    def title(self) -> str:
        return self.path.stem

    @property
    def readable(self) -> Path:
        return self.ocr_path or self.path


@dataclass
class Report:
    stages: dict[str, int] = field(default_factory=dict)
    unassigned: list[str] = field(default_factory=list)
    vanished: list[str] = field(default_factory=list)
    chunks: int = 0
    empty: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    # One row per stage: wall time, model calls, tokens, watt-hours. Written to
    # state.db when the run ends, and read back by `studykb stats`.
    run: metrics.Run | None = None

    # `stages` counts what a stage produced — pages, captions, chunks — which is
    # what the CLI table has always shown. `processed` counts the sources it
    # touched, which is what a per-source cost needs.
    processed: dict[str, int] = field(default_factory=dict)

    def bump(self, stage: str, n: int = 1) -> None:
        self.stages[stage] = self.stages.get(stage, 0) + n
        self.processed[stage] = self.processed.get(stage, 0) + 1


# --------------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------------
def discover(corpus: Corpus, modules: list[cal.Module]) -> tuple[list[Source], list[str]]:
    """Glob the corpus root and assign each file to a module."""
    by_date = {lec.date.isoformat(): lec.module for m in modules for lec in m.lectures if lec.date}
    overrides = _read_manifest(corpus.manifest_dir / "MANIFEST.md")

    found: dict[str, Source] = {}
    for rule in corpus.sources:
        if not rule.enabled:
            continue
        for path in sorted(corpus.root.glob(rule.glob)):
            if not path.is_file() or path.suffix.lower() not in extract.SUPPORTED:
                continue
            rel = str(path.relative_to(corpus.root))
            if rel in found or _excluded(rel, corpus.exclude):
                continue
            override = overrides.get(rel)
            if override and override.get("enabled") is False:
                continue
            type_ = (override or {}).get("type") or rule.type
            found[rel] = Source(
                path=path,
                rel=rel,
                type=type_,
                # A file reclassified as slides in the manifest must get the
                # slide treatment too, or the override only half works.
                vision="force" if type_ == "slides" else rule.vision,
                module=(override or {}).get("module") or _module_for(rel, corpus, by_date),
            )

    sources = list(found.values())
    unassigned = [s.rel for s in sources if not s.module]
    return sources, unassigned


def _excluded(rel: str, patterns: list[str]) -> bool:
    """Match an exclude pattern against the path.

    fnmatch rather than Path.glob: pathlib's ``**`` expands to directories only,
    so ``test-corpus/**`` excluded nothing at all and the review set was being
    indexed as course material. Here ``*`` crosses separators, so
    ``test-corpus/**`` and ``admin/**`` cover everything beneath them.
    """
    return any(fnmatch(rel, pattern) for pattern in patterns)


def _module_for(rel: str, corpus: Corpus, by_date: dict[str, str]) -> str | None:
    for rule in corpus.module_rules:
        if not rule.pattern:
            continue
        match = re.search(rule.pattern, "/" + rel)
        if not match:
            continue
        groups = match.groupdict()
        if rule.resolve == "calendar_date" and (date := groups.get("date")):
            if module := by_date.get(date):
                return module
        elif module := groups.get("module"):
            return f"M{int(module)}"
    return None


def _read_manifest(path: Path) -> dict[str, dict]:
    """Hand-written overrides, as a markdown table: | path | module | type | enabled |.

    This is where files the regexes cannot place get assigned, and where a source
    is switched off. Deciding what belongs in the corpus is a manifest decision,
    never a code one.
    """
    if not path.exists():
        return {}
    out: dict[str, dict] = {}
    for line in path.read_text().splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0].lower() in ("path", "file") or set(cells[0]) <= set("-: "):
            continue
        type_ = cells[2] if len(cells) > 2 and cells[2] else None
        enabled = cells[3].lower() not in ("false", "no", "0") if len(cells) > 3 and cells[3] else True
        out[cells[0]] = {"module": cells[1] or None, "type": type_, "enabled": enabled}
    return out


# --------------------------------------------------------------------------
# Ingest
# --------------------------------------------------------------------------
def ingest(
    cfg: Config,
    corpus: Corpus,
    *,
    dry_run: bool = False,
    only: set[str] | None = None,
    log=print,
) -> Report:
    report = Report()
    modules = _load_calendar(cfg, corpus, log)
    sources, unassigned = discover(corpus, modules)
    report.unassigned = unassigned
    fp = cfg.fingerprint(prompts.version())
    work = cfg.work

    if dry_run:
        log(f"{len(sources)} sources under {corpus.root}")
        for stage in ("ocr", "extract", "asr_cleanup", "vision", "embed"):
            report.stages[stage] = 0
        with State(cfg.storage.state_db) as st:
            for src in sources:
                src.sha = file_sha(src.path)
                for stage in ("ocr", "extract", "asr_cleanup", "vision", "embed"):
                    if not (
                        _stage_applies(stage, src, cfg)
                        and st.needs(src.rel, stage, src.sha, _effective_fp(fp, stage, src, cfg))
                    ):
                        continue
                    # The OCR stage checks every PDF but rewrites almost none;
                    # reporting the checks would badly overstate the work.
                    if stage == "ocr" and not extract.ocr.needs_ocr(src.path, cfg):
                        continue
                    report.bump(stage)
        return report

    run = metrics.Run(corpus=corpus.domain)
    report.run = run

    with State(cfg.storage.state_db) as st, LLM(cfg) as llm:
        for src in sources:
            src.sha = file_sha(src.path)
            st.see(src.rel, src.sha, src.type, src.module)
        report.vanished = st.vanished({s.rel for s in sources})

        _write_syllabus(cfg, modules, log)

        # Order matters: each stage reads what the one above it wrote.
        stage_fns = {
            "ocr": lambda: _stage_ocr(cfg, sources, st, fp, work, report, log),
            "extract": lambda: _stage_extract(cfg, sources, st, fp, work, report, log),
            "asr_cleanup": lambda: _stage_asr(cfg, corpus, modules, sources, st, fp, work, llm, report, log),
            "vision": lambda: _stage_vision(cfg, sources, st, fp, work, llm, report, log),
            "embed": lambda: _stage_embed(cfg, sources, st, fp, work, llm, report, log),
        }
        for name, fn in stage_fns.items():
            if not _wanted(name, only):
                continue
            before_errors = len(report.errors)
            with run.stage(name, llm) as m:
                fn()
            m.sources = report.processed.get(name, 0)
            m.items = report.stages.get(name, 0)
            m.errors = len(report.errors) - before_errors
        run.save(st.conn)
        _write_sources(cfg, modules, st, {s.rel for s in sources}, log)

    return report


def _wanted(stage: str, only: set[str] | None) -> bool:
    return only is None or stage in only


# A stage consumes the output of the stages above it, so its gate has to move
# when theirs does. Without this, re-captioning a deck leaves the new captions
# sitting in a file that embed never reads again, and the index quietly keeps
# yesterday's content while every run reports success.
_UPSTREAM: dict[str, tuple[str, ...]] = {
    "extract": ("ocr",),
    "asr_cleanup": ("extract",),
    "vision": ("extract",),
    "embed": ("extract", "asr_cleanup", "vision"),
}


# Facts about one source that a stage bakes into its output, but that no config
# fingerprint covers. Without them, correcting a MANIFEST.md entry changes
# nothing at all: the gate still reads "already done" and the old value stays in
# the index. That silently broke the recovery the CLI itself recommends —
# "set type: slides in MANIFEST.md to force captioning" did not force anything.
_PER_SOURCE: dict[str, tuple[str, ...]] = {
    "vision": ("vision",),          # type: slides is what turns captioning on
    "embed": ("module", "type"),    # both are written into every chunk payload
}


def _effective_fp(fp: dict[str, str], stage: str, src: Source, cfg: Config) -> str:
    """Fingerprint of a stage plus every upstream stage that feeds this source."""
    parts = [fp[stage]]
    for up in _UPSTREAM.get(stage, ()):
        if _stage_applies(up, src, cfg):
            parts.append(fp[up])
    parts += [str(getattr(src, field)) for field in _PER_SOURCE.get(stage, ())]
    return "|".join(parts)


def _stage_applies(stage: str, src: Source, cfg: Config) -> bool:
    if stage == "ocr":
        return cfg.extract.ocr.enabled and src.path.suffix.lower() == ".pdf"
    if stage == "asr_cleanup":
        return cfg.transcript.asr_cleanup and src.type == "transcript"
    if stage == "vision":
        return cfg.extract.vision.enabled and src.vision != "never" and src.path.suffix.lower() == ".pdf"
    return True


def _units_file(work: Path, src: Source, kind: str) -> Path:
    return work / kind / f"{src.sha[:WORK_SHA_CHARS]}-{Path(src.rel).stem[:WORK_STEM_CHARS]}.json"


def _save_units(path: Path, units: list[Unit]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([u.__dict__ for u in units], ensure_ascii=False))


def _load_units(path: Path) -> list[Unit]:
    if not path.exists():
        return []
    return [Unit(**d) for d in json.loads(path.read_text())]


# -- stage 1: OCR ----------------------------------------------------------
def _stage_ocr(cfg, sources, st, fp, work, report, log) -> None:
    # Sources already OCR'd in a previous run must still point at their copy.
    for src in sources:
        if ref := st.output_ref(src.rel, "ocr"):
            if (path := Path(ref)).exists():
                src.ocr_path = path

    todo = [s for s in sources if _stage_applies("ocr", s, cfg) and st.needs(s.rel, "ocr", s.sha, _effective_fp(fp, "ocr", s, cfg))]
    if not todo:
        return
    log(f"[ocr] checking {len(todo)} PDFs for a missing text layer")
    for src in todo:
        out_ref = None
        try:
            if extract.ocr.needs_ocr(src.path, cfg):
                log(f"[ocr] {src.rel}")
                src.ocr_path = extract.ocr.run_ocr(
                    src.path, work / "ocr" / f"{src.sha[:WORK_SHA_CHARS]}.pdf", cfg
                )
                out_ref = str(src.ocr_path)
                report.bump("ocr")
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"ocr {src.rel}: {exc}")
            continue
        st.mark(src.rel, "ocr", src.sha, _effective_fp(fp, "ocr", src, cfg), out_ref)


# -- stage 2: extract ------------------------------------------------------
def _stage_extract(cfg, sources, st, fp, work, report, log) -> None:
    todo = [s for s in sources if st.needs(s.rel, "extract", s.sha, _effective_fp(fp, "extract", s, cfg))]
    if not todo:
        return
    log(f"[extract] {len(todo)} sources")
    for src in todo:
        try:
            units = extract.extract_units(src.readable, cfg)
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"extract {src.rel}: {exc}")
            continue
        out = _units_file(work, src, "units")
        _save_units(out, units)
        _write_extracted_markdown(cfg, src, units)
        st.mark(src.rel, "extract", src.sha, _effective_fp(fp, "extract", src, cfg), str(out))
        report.bump("extract")


def _write_extracted_markdown(cfg: Config, src: Source, units: list[Unit]) -> None:
    """Mirror the extraction into the vault.

    Readable in Obsidian and greppable without Qdrant running, which matters the
    day the container is down and you still want to study.
    """
    out = cfg.storage.vault / "90-extracted" / (src.module or "unassigned") / f"{Path(src.rel).stem}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    body = [f"# {src.title}", "", f"> source: `{src.rel}` · type: {src.type}", ""]
    for unit in units:
        if unit.text.strip():
            body += [f"## {unit.locator}" + (f" — {unit.heading}" if unit.heading else ""), "", unit.text, ""]
    out.write_text("\n".join(body))


# -- stage 3: ASR cleanup --------------------------------------------------
def _stage_asr(cfg, corpus, modules, sources, st, fp, work, llm, report, log) -> None:
    todo = [
        s for s in sources
        if _stage_applies("asr_cleanup", s, cfg) and st.needs(s.rel, "asr_cleanup", s.sha, _effective_fp(fp, "asr_cleanup", s, cfg))
    ]
    if not todo:
        return
    glossary = corpus.glossary + cal.glossary_terms(modules)
    tpl = prompts.get("fix_asr")
    log(f"[asr] repairing captions for {len(todo)} transcripts with {cfg.models.llm.name}")
    for src in todo:
        units = _load_units(_units_file(work, src, "units"))
        if not units:
            continue
        lecture = next(
            (lec.topic for m in modules if m.id == src.module for lec in m.lectures if lec.topic), ""
        )
        fixed = extract.asr.correct(units, glossary, llm, tpl, lecture)
        out = _units_file(work, src, "asr")
        _save_units(out, fixed)
        st.mark(src.rel, "asr_cleanup", src.sha, _effective_fp(fp, "asr_cleanup", src, cfg), str(out))
        report.bump("asr_cleanup", len(fixed))
    llm.unload(cfg.models.llm.name)


# -- stage 4: vision -------------------------------------------------------
def _stage_vision(cfg, sources, st, fp, work, llm, report, log) -> None:
    todo = [
        s for s in sources
        if _stage_applies("vision", s, cfg) and st.needs(s.rel, "vision", s.sha, _effective_fp(fp, "vision", s, cfg))
    ]
    if not todo:
        return
    tpl = prompts.get("caption_slide")
    log(f"[vision] captioning figures in {len(todo)} sources with {cfg.models.vlm.name}")
    for src in todo:
        units = _load_units(_units_file(work, src, "units"))
        if not units:
            continue
        prompt = tpl.render(source=src.title, type=src.type)
        try:
            captions = extract.vision.caption_pages(src.readable, units, cfg, llm, prompt, src.vision)
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"vision {src.rel}: {exc}")
            continue
        out = _units_file(work, src, "captions")
        _save_units(out, captions)
        st.mark(src.rel, "vision", src.sha, _effective_fp(fp, "vision", src, cfg), str(out))
        report.bump("vision", len(captions))
    llm.unload(cfg.models.vlm.name)
    if cfg.models.vlm.fallback:
        llm.unload(cfg.models.vlm.fallback)


# -- stage 5: chunk + embed ------------------------------------------------
def _stage_embed(cfg, sources, st, fp, work, llm, report, log) -> None:
    client = index.connect(cfg)
    index.ensure_collection(client, cfg)

    # If the collection is empty but state says everything is indexed, the state
    # is lying: a dropped collection, a lost volume, a Qdrant upgrade that could
    # not read its own storage. Believing it would leave the index permanently
    # empty with every run reporting success.
    if index.total(client, cfg) == 0:
        cleared = st.clear_stage("embed")
        if cleared:
            log(f"[embed] collection is empty but {cleared} sources were marked indexed — reindexing all")

    todo = [s for s in sources if st.needs(s.rel, "embed", s.sha, _effective_fp(fp, "embed", s, cfg))]
    if not todo:
        return
    log(f"[embed] indexing {len(todo)} sources with {cfg.models.embed.name}")

    for src in todo:
        chunks = list(_chunks_for(cfg, src, work))
        if not chunks:
            # A source that yields nothing is the quietest possible failure: it
            # looks like a clean run and the material is simply absent from
            # every search. Always surface it.
            report.empty.append(src.rel)
            continue
        try:
            vectors = llm.embed([c.text for c in chunks])
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"embed {src.rel}: {exc}")
            continue
        # Drop first: a shorter re-extraction would otherwise leave the tail of
        # the previous run's chunks orphaned in the collection.
        index.drop_source(client, cfg, src.rel)
        index.upsert(client, cfg, chunks, vectors)
        st.mark(src.rel, "embed", src.sha, _effective_fp(fp, "embed", src, cfg), str(len(chunks)))
        report.bump("embed")
        report.chunks += len(chunks)


def _chunks_for(cfg: Config, src: Source, work: Path) -> Iterator:
    """Body text (ASR-corrected where available) plus vision captions."""
    asr = _units_file(work, src, "asr")
    units = _load_units(asr) if asr.exists() else _load_units(_units_file(work, src, "units"))
    yield from chunking.to_chunks(
        units, source=src.rel, source_title=src.title, type_=src.type, module=src.module, cfg=cfg.chunk
    )
    captions = _load_units(_units_file(work, src, "captions"))
    yield from chunking.to_chunks(
        captions, source=src.rel, source_title=src.title, type_="caption", module=src.module, cfg=cfg.chunk
    )


# --------------------------------------------------------------------------
# Calendar / syllabus
# --------------------------------------------------------------------------
def _load_calendar(cfg: Config, corpus: Corpus, log) -> list[cal.Module]:
    if not corpus.calendar:
        return []
    path = corpus.root / corpus.calendar.source
    if not path.exists():
        log(f"[calendar] {path} not found — modules and glossary will be empty")
        return []
    return cal.parse(path, corpus.calendar)


def _write_sources(cfg: Config, modules: list[cal.Module], st: State, present: set[str], log) -> None:
    """Rewrite SOURCES.md: every known file, grouped by module, with its chunk count."""
    rows = st.conn.execute(
        "SELECT s.source, s.type, s.module, e.output_ref, e.done_at FROM seen_sources s"
        " LEFT JOIN stage_state e ON e.source = s.source AND e.stage = 'embed'"
        " ORDER BY s.module IS NULL, s.module, s.type, s.source"
    ).fetchall()
    titles = {m.id: m.title for m in modules}
    indexed = sum(1 for r in rows if r[3] is not None and r[0] in present)
    lines = [f"# Indexed sources — {indexed} of {len(present)} files", "",
             f"Rewritten by every `studykb ingest`. Last: {time.strftime('%Y-%m-%d %H:%M')}.", ""]
    current = object()
    for source, type_, module, chunks, done_at in rows:
        if module != current:
            current = module
            lines += ["", f"## {module or 'No module'} {titles.get(module, '')}".rstrip(), "",
                      "| file | type | chunks | indexed |", "|---|---|---:|---|"]
        when = time.strftime("%Y-%m-%d", time.localtime(done_at)) if done_at else "—"
        if source not in present:
            when = "missing from disk"
        lines.append(f"| {source} | {type_} | {chunks or '—'} | {when} |")
    path = cfg.storage.vault / "SOURCES.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    log(f"[sources] {indexed} indexed -> {path}")


def _write_syllabus(cfg: Config, modules: list[cal.Module], log) -> None:
    """Write one syllabus page per module, never clobbering your own notes."""
    if not modules:
        return
    out_dir = cfg.storage.vault / "00-syllabus"
    out_dir.mkdir(parents=True, exist_ok=True)
    for module_id, text in cal.to_markdown(modules).items():
        path = out_dir / f"{module_id}.md"
        if path.exists() and "## Notes" in (existing := path.read_text()):
            notes = existing.split("## Notes", 1)[1]
            text = text.split("## Notes", 1)[0] + "## Notes" + notes
        path.write_text(text)
    log(f"[calendar] {len(modules)} modules -> {out_dir}")

"""Reviewable reports, so a human signs off before the index is trusted.

Three things go wrong quietly in this pipeline and none of them raise an error:

* **extraction** drops a page, or returns a copyright footer and calls it
  content;
* **captions** describe a figure that is not there — a 7B vision model handed a
  cover page will pattern-complete from the title;
* **retrieval** returns something plausible from the wrong source.

Each report is markdown written into the corpus, next to the rendered pages, so
it opens in Obsidian with the page image and the model's claim about it on the
same screen. Checking a caption against the page is the only way to know.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import yaml

from . import index, search as search_mod
from .chunk import CHARS_PER_TOKEN
from .config import Config, Corpus
from .limits import (
    CHUNK_CLOSES,
    CHUNK_OPENS,
    CHUNK_SEAM_MIN,
    EMPTY_PAGES_LISTED,
    EXTRACTION_PREVIEW,
    LOST_PAGES_LISTED,
    MISSING_LOCATORS_LISTED,
    NO_CHUNKS_LISTED,
    RETRIEVAL_K,
    RETRIEVAL_PASSAGE,
    RETRIEVAL_TITLE,
    SLUG_CHARS,
    TINY_CHUNKS_LISTED,
)
from .llm import LLM
from .pipeline import Source, _chunks_for, _load_calendar, _units_file, discover
from .state import file_sha


def _sources(cfg: Config, corpus: Corpus) -> list[Source]:
    sources, _ = discover(corpus, _load_calendar(cfg, corpus, log=lambda *_: None))
    for src in sources:
        src.sha = file_sha(src.path)
    return sources


def _load_units(path: Path) -> list[dict]:
    return json.loads(path.read_text()) if path.exists() else []


def _slug(rel: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in Path(rel).stem)[:SLUG_CHARS]


def _render_for_review(src: Source, cap: dict, cfg: Config, out_dir: Path) -> Path | None:
    """Render the page this caption claims to describe, next to the report."""
    from .extract.vision import render_page

    page_no = cap.get("page_no")
    if not page_no or src.path.suffix.lower() != ".pdf":
        return None
    # Slug the filename: source titles here contain spaces, commas and braces,
    # which break the image link in every markdown renderer except Obsidian.
    target = out_dir / f"p{page_no:04d}.png"
    if target.exists():
        return target
    try:
        rendered = render_page(src.path, page_no, cfg, out_dir)
        return rendered.rename(target)
    except Exception:  # noqa: BLE001 - a page that will not render is not a reason to lose the report
        return None


# --------------------------------------------------------------------------
# 0. Summary — the one screen that says whether anything is wrong
# --------------------------------------------------------------------------
@dataclass
class Check:
    ok: bool
    name: str
    detail: str

    @property
    def mark(self) -> str:
        return "✅" if self.ok else "⚠️"


def summary(cfg: Config, corpus: Corpus) -> tuple[list[list[str]], list[Check]]:
    """Per-source numbers, plus the checks that catch silent damage.

    Every failure this pipeline has actually produced was invisible in a run
    that reported success: a deck indexed as nothing, a caption overwriting the
    page it described, a source discovered from the wrong corpus. Each of those
    is one line here.
    """
    rev = cfg.review
    work = cfg.work
    client = index.connect(cfg)
    sources = _sources(cfg, corpus)
    try:
        indexed_by_source = index.counts_by(client, cfg, "source", [s.rel for s in sources])
    except Exception:  # noqa: BLE001 - collection may not exist yet
        indexed_by_source = {}

    rows: list[list[str]] = []
    produced_total = 0
    indexed_total = 0
    no_chunks: list[str] = []
    lost_pages: list[str] = []
    trivial_captions = 0
    captions_total = 0
    tiny_chunks = 0

    for src in sources:
        units = _load_units(_units_file(work, src, "units"))
        caps = [c for c in _load_units(_units_file(work, src, "captions")) if c["text"].strip()]
        captions_total += len(caps)
        trivial_captions += sum(1 for c in caps if len(c["text"]) < rev.trivial_caption_chars)

        produced = list(_chunks_for(cfg, src, work))
        produced_total += len(produced)
        tiny_chunks += sum(1 for c in produced if len(c.text) < rev.tiny_chunk_chars)
        indexed = indexed_by_source.get(src.rel, 0)
        indexed_total += indexed

        pages_with_text = sum(1 for u in units if u["text"].strip())
        covered = {c.locator for c in produced}
        missing = [u["locator"] for u in units if u["text"].strip() and u["locator"] not in covered]
        if missing:
            lost_pages.append(
                f"{src.rel}: {len(missing)} ({', '.join(missing[:MISSING_LOCATORS_LISTED])})"
            )
        if not indexed:
            no_chunks.append(src.rel)

        chars = sum(len(u["text"].strip()) for u in units)
        rows.append([
            src.rel, src.type, src.module or "—",
            f"{pages_with_text}/{len(units)}",
            f"{chars // max(len(units), 1):,}",
            str(len(caps)),
            f"{indexed}" + ("" if indexed == len(produced) else f"/{len(produced)}"),
        ])

    tiny_ok = tiny_chunks <= max(produced_total * rev.tiny_chunk_share, rev.tiny_chunk_floor)
    captions_ok = trivial_captions <= captions_total * rev.trivial_caption_share
    checks = [
        Check(not no_chunks, "every source is indexed",
              "all sources have chunks" if not no_chunks
              else f"{len(no_chunks)} indexed nowhere: {', '.join(no_chunks[:NO_CHUNKS_LISTED])}"),
        Check(produced_total == indexed_total, "nothing was lost on the way in",
              f"{produced_total} chunks produced, {indexed_total} in the collection"
              + ("" if produced_total == indexed_total
                 else " — a mismatch means chunks share an id and overwrote each other")),
        Check(not lost_pages, "no page with text was dropped",
              "every page carrying text produced a chunk" if not lost_pages
              else "; ".join(lost_pages[:LOST_PAGES_LISTED])),
        Check(tiny_ok, "chunks are worth indexing",
              f"{tiny_chunks} of {produced_total} chunks are under {rev.tiny_chunk_chars} characters"
              + ("" if tiny_ok
                 else " — mostly title pages and dividers, they dilute retrieval")),
        Check(captions_ok, "captions carry content",
              f"{captions_total} captions, {trivial_captions} trivial (\"Cover page.\", \"Blank page.\")"
              + ("" if captions_ok
                 else " — the graphics floor is letting empty pages through")),
    ]
    return rows, checks


# "pages" is written as with-text/total, so a deck that extracted to nothing
# reads as 0/137 at a glance.
SUMMARY_COLUMNS = ["source", "type", "mod", "pages", "ch/pg", "cap", "chunks"]


def summary_report(cfg: Config, corpus: Corpus, out: Path) -> Path:
    rows, checks = summary(cfg, corpus)
    lines = [
        f"# Review summary — {corpus.domain}",
        "",
        "## Checks",
        "",
    ]
    for c in checks:
        lines.append(f"- {c.mark} **{c.name}** — {c.detail}")
    lines += ["", "## Sources", "", "| " + " | ".join(SUMMARY_COLUMNS) + " |",
              "|" + "---|" * len(SUMMARY_COLUMNS)]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    lines += [
        "",
        "`pages` is with-text/total · `ch/pg` characters per page · `cap` captions ·",
        "`chunks` shows indexed/produced when the two differ.",
        "",
        "## Where to look next",
        "",
        "| question | file |",
        "|---|---|",
        "| did a page lose its text? | `extraction.md` |",
        "| where does one chunk end and the next begin? | `chunks.md` |",
        "| is a caption describing something that is not there? | `captions.md` |",
        "| does search return the right passage? | `retrieval.md` |",
        "",
    ]
    path = out / "SUMMARY.md"
    path.write_text("\n".join(lines))
    return path


# --------------------------------------------------------------------------
# 1. Extraction
# --------------------------------------------------------------------------
def extraction_report(cfg: Config, corpus: Corpus, out: Path, preview: int = EXTRACTION_PREVIEW) -> Path:
    """Per page: how much text came out, and the start of it.

    Empty and near-empty pages are called out at the top, because a page that
    extracted to nothing is indexed as nothing and searching will never tell you.
    """
    work = cfg.work
    lines = ["# Extraction review", "", "Check that nothing meaningful was dropped.", ""]

    for src in _sources(cfg, corpus):
        units = _load_units(_units_file(work, src, "units"))
        if not units:
            lines += [f"## {src.rel}", "", "> **Not extracted.** Run `studykb ingest --only extract`.", ""]
            continue

        empty = [u["locator"] for u in units if not u["text"].strip()]
        chars = sum(len(u["text"].strip()) for u in units)
        lines += [
            f"## {src.rel}",
            "",
            f"- type: `{src.type}` · module: `{src.module or '—'}`",
            f"- {len(units)} pages, {chars:,} characters, {chars // max(len(units), 1):,} per page",
        ]
        if empty:
            share = len(empty) / len(units)
            flag = "🔴" if share > cfg.review.empty_pages_alarm_share else "⚠️"
            lines.append(f"- {flag} **{len(empty)} pages extracted to nothing** ({share:.0%}): "
                         f"{', '.join(empty[:EMPTY_PAGES_LISTED])}"
                         + (" …" if len(empty) > EMPTY_PAGES_LISTED else ""))
        lines.append("")

        lines += ["| page | chars | text starts |", "|---|---:|---|"]
        for unit in units:
            text = " ".join(unit["text"].split())[:preview]
            lines.append(f"| {unit['locator']} | {len(unit['text'].strip())} | {text.replace('|', '\\|') or '—'} |")
        lines.append("")

    path = out / "extraction.md"
    path.write_text("\n".join(lines))
    return path


# --------------------------------------------------------------------------
# 2. Captions
# --------------------------------------------------------------------------
def caption_report(cfg: Config, corpus: Corpus, out: Path) -> Path:
    """Each caption next to a picture of the page it describes.

    Open it in Obsidian and read down: the image and the claim are adjacent, so
    a hallucinated circuit is obvious in a second. Nothing here is a
    transcription — captions exist to make a figure findable.
    """
    work = cfg.work
    lines = [
        "# Caption review",
        "",
        "Each page image is followed by what the vision model said about it.",
        "Mark anything wrong — a caption that describes something not in the picture",
        "is worse than no caption, because it is indexed as if it were content.",
        "",
    ]
    total = 0
    skipped: list[str] = []
    for src in _sources(cfg, corpus):
        captions = [c for c in _load_units(_units_file(work, src, "captions")) if c["text"].strip()]
        if not captions:
            skipped.append(f"- `{src.rel}` — {_why_no_captions(src, cfg, work)}")
            continue
        lines += [f"## {src.rel}", "", f"{len(captions)} captions · module `{src.module or '—'}`", ""]
        pages_dir = out / "pages" / _slug(src.rel)
        pages_dir.mkdir(parents=True, exist_ok=True)
        for cap in captions:
            total += 1
            lines += [f"### {cap['locator']}", ""]
            png = _render_for_review(src, cap, cfg, pages_dir)
            # Relative to the report, so it renders in Obsidian and in any
            # markdown viewer without an absolute path.
            lines += [f"![{cap['locator']}]({png.relative_to(out).as_posix()})", ""] if png else [
                "> could not render this page", ""
            ]
            lines += [cap["text"], "", "---", ""]

    if skipped:
        # Omitting these silently reads as "the source was not processed".
        # Usually it means captioning was never meant to run on it.
        lines += ["## Sources with no captions", "", *skipped, ""]

    lines.insert(1, "")
    lines.insert(1, f"**{total} captions to review.**")
    path = out / "captions.md"
    path.write_text("\n".join(lines))
    return path


def _why_no_captions(src: Source, cfg: Config, work: Path) -> str:
    """Say why, so an absence is never mistaken for a failure."""
    if not cfg.extract.vision.enabled:
        return "captioning is switched off globally (`extract.vision.enabled`)"
    if src.vision == "never":
        return (f"captioning is off for `{src.type}` sources — on prose the model "
                f"describes covers and invents figures, so it is not run")
    if src.path.suffix.lower() != ".pdf":
        return f"captioning only handles PDFs, this is `{src.path.suffix}`"
    if not _units_file(work, src, "captions").exists():
        return "not captioned yet — run `studykb ingest --only vision`"
    return (f"no page reached the graphics floor of {cfg.extract.vision.min_graphics} "
            f"(`extract.vision.min_graphics`) — nothing to describe")


# --------------------------------------------------------------------------
# 2b. Chunks — the unit retrieval actually returns
# --------------------------------------------------------------------------
def chunks_report(cfg: Config, corpus: Corpus, out: Path) -> Path:
    """Show the seams, not the text.

    A page is not what search returns — a chunk is, and a chunk can begin and
    end anywhere. The text itself is already in extraction.md, so this shows
    each chunk's opening and closing words: read down the pairs and a cut
    landing mid-derivation is obvious, while a full dump of 488 chunks is not.
    """
    work = cfg.work
    lines = [
        "# Chunk review",
        "",
        "What search actually returns. Each row is one indexed chunk, with the",
        "words it opens and closes on — a cut landing mid-sentence or mid-formula",
        "shows up in the pair, without reading the whole text.",
        "",
        "`chunk.target_tokens` is a **ceiling**, not a target: a page shorter than",
        "it is kept whole, so on ordinary pages one chunk is one page and every",
        "locator is exact. Transcripts and captions are never split.",
        "",
    ]

    for src in _sources(cfg, corpus):
        chunks = list(_chunks_for(cfg, src, work))
        if not chunks:
            continue
        sizes = sorted(len(c.text) for c in chunks)
        pages = len({c.locator for c in chunks})
        ceiling = cfg.chunk.target_tokens * CHARS_PER_TOKEN
        under = sum(1 for n in sizes if n < ceiling)
        tiny = [c for c in chunks if len(c.text) < cfg.review.tiny_chunk_chars]
        lines += [
            f"## {src.rel}",
            "",
            f"- {len(chunks)} chunks over {pages} locators · median {sizes[len(sizes) // 2]:,} chars "
            f"({sizes[0]:,} smallest, {sizes[-1]:,} largest)",
            f"- {under}/{len(sizes)} are below the {ceiling:,}-character ceiling, so the splitter "
            f"mostly does not fire: **one page, one chunk**, and every locator is exact",
        ]
        if tiny:
            lines.append(
                f"- {len(tiny)} chunks under {cfg.review.tiny_chunk_chars} characters — title pages "
                f"and part dividers ({', '.join(c.locator for c in tiny[:TINY_CHUNKS_LISTED])}). "
                f"Index noise, not content."
            )
        lines += [
            "",
            "| # | locator | type | prov | chars | opens with … closes with |",
            "|---:|---|---|---|---:|---|",
        ]
        for i, c in enumerate(chunks, 1):
            text = " ".join(c.text.split())
            opens = text[:CHUNK_OPENS].replace("|", "\\|")
            closes = text[-CHUNK_CLOSES:].replace("|", "\\|") if len(text) > CHUNK_SEAM_MIN else ""
            seam = f"{opens} **…** {closes}" if closes else opens
            lines.append(
                f"| {i} | `{c.locator}` | {c.type} | {c.provenance} | {len(c.text):,} | {seam} |"
            )
        lines.append("")

    path = out / "chunks.md"
    path.write_text("\n".join(lines))
    return path


# --------------------------------------------------------------------------
# 3. Retrieval
# --------------------------------------------------------------------------
def retrieval_report(cfg: Config, corpus: Corpus, out: Path, queries_file: Path) -> Path:
    """Run a list of queries and lay the answers out for checking.

    A query file is a list of `{query, module?, type?, expect?}`. `expect` is a
    substring of the source you believe should come back — it is a prompt to
    look, not a pass/fail: retrieval that surfaces a better source than the one
    you guessed is not a failure.
    """
    queries = yaml.safe_load(queries_file.read_text()) or []
    lines = [
        "# Retrieval review",
        "",
        f"{len(queries)} queries from `{queries_file.name}`.",
        "**Open each locator and confirm the passage is really there.** A citation",
        "that does not survive being checked makes every note built on it worthless.",
        "",
    ]

    with LLM(cfg) as llm:
        client = index.connect(cfg)
        for q in queries:
            hits = search_mod.search(
                client, cfg, llm, q["query"],
                module=q.get("module"), type_=q.get("type"), k=q.get("k", RETRIEVAL_K),
            )
            lines += [f"## {q['query']}", ""]
            filters = [f"{k}={v}" for k, v in q.items() if k in ("module", "type")]
            if filters:
                lines.append(f"filters: {', '.join(filters)}")
            if expect := q.get("expect"):
                found = any(expect.lower() in h.source_title.lower() for h in hits)
                lines.append(f"expected `{expect}` — {'✅ present' if found else '❌ absent'}")
            lines += ["", "| # | source | locator | provenance | score | passage |", "|---|---|---|---|---:|---|"]
            for i, h in enumerate(hits, 1):
                text = " ".join(h.text.split())[:RETRIEVAL_PASSAGE].replace("|", "\\|")
                lines.append(
                    f"| {i} | {h.source_title[:RETRIEVAL_TITLE]} | `{h.locator}` | {h.provenance} "
                    f"| {h.score:.3f} | {text} |"
                )
            lines.append("")

    path = out / "retrieval.md"
    path.write_text("\n".join(lines))
    return path

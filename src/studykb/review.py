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
from .config import Config, Corpus
from .llm import LLM
from .pipeline import Source, _load_calendar, _units_file, discover
from .state import State, file_sha


@dataclass
class ReviewPaths:
    root: Path

    def file(self, name: str) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        return self.root / name


def _sources(cfg: Config, corpus: Corpus) -> list[Source]:
    sources, _ = discover(corpus, _load_calendar(cfg, corpus, log=lambda *_: None))
    for src in sources:
        src.sha = file_sha(src.path)
    return sources


def _load_units(path: Path) -> list[dict]:
    return json.loads(path.read_text()) if path.exists() else []


def _slug(rel: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in Path(rel).stem)[:60]


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
# 1. Extraction
# --------------------------------------------------------------------------
def extraction_report(cfg: Config, corpus: Corpus, out: ReviewPaths, preview: int = 400) -> Path:
    """Per page: how much text came out, and the start of it.

    Empty and near-empty pages are called out at the top, because a page that
    extracted to nothing is indexed as nothing and searching will never tell you.
    """
    work = cfg.storage.state_db.parent / "work"
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
            flag = "🔴" if share > 0.5 else "⚠️"
            lines.append(f"- {flag} **{len(empty)} pages extracted to nothing** ({share:.0%}): {', '.join(empty[:12])}"
                         + (" …" if len(empty) > 12 else ""))
        lines.append("")

        lines += ["| page | chars | text starts |", "|---|---:|---|"]
        for unit in units:
            text = " ".join(unit["text"].split())[:preview]
            lines.append(f"| {unit['locator']} | {len(unit['text'].strip())} | {text.replace('|', '\\|') or '—'} |")
        lines.append("")

    path = out.file("extraction.md")
    path.write_text("\n".join(lines))
    return path


# --------------------------------------------------------------------------
# 2. Captions
# --------------------------------------------------------------------------
def caption_report(cfg: Config, corpus: Corpus, out: ReviewPaths) -> Path:
    """Each caption next to a picture of the page it describes.

    Open it in Obsidian and read down: the image and the claim are adjacent, so
    a hallucinated circuit is obvious in a second. Nothing here is a
    transcription — captions exist to make a figure findable.
    """
    work = cfg.storage.state_db.parent / "work"
    lines = [
        "# Caption review",
        "",
        "Each page image is followed by what the vision model said about it.",
        "Mark anything wrong — a caption that describes something not in the picture",
        "is worse than no caption, because it is indexed as if it were content.",
        "",
    ]
    total = 0
    for src in _sources(cfg, corpus):
        captions = _load_units(_units_file(work, src, "captions"))
        captions = [c for c in captions if c["text"].strip()]
        if not captions:
            continue
        lines += [f"## {src.rel}", "", f"{len(captions)} captions · module `{src.module or '—'}`", ""]
        pages_dir = out.root / "pages" / _slug(src.rel)
        pages_dir.mkdir(parents=True, exist_ok=True)
        for cap in captions:
            total += 1
            lines += [f"### {cap['locator']}", ""]
            png = _render_for_review(src, cap, cfg, pages_dir)
            # Relative to the report, so it renders in Obsidian and in any
            # markdown viewer without an absolute path.
            lines += [f"![{cap['locator']}]({png.relative_to(out.root).as_posix()})", ""] if png else [
                "> could not render this page", ""
            ]
            lines += [cap["text"], "", "---", ""]

    lines.insert(1, "")
    lines.insert(1, f"**{total} captions to review.**")
    path = out.file("captions.md")
    path.write_text("\n".join(lines))
    return path


# --------------------------------------------------------------------------
# 3. Retrieval
# --------------------------------------------------------------------------
def retrieval_report(cfg: Config, corpus: Corpus, out: ReviewPaths, queries_file: Path) -> Path:
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
                module=q.get("module"), type_=q.get("type"), k=q.get("k", 5),
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
                text = " ".join(h.text.split())[:220].replace("|", "\\|")
                lines.append(
                    f"| {i} | {h.source_title[:40]} | `{h.locator}` | {h.provenance} | {h.score:.3f} | {text} |"
                )
            lines.append("")

    path = out.file("retrieval.md")
    path.write_text("\n".join(lines))
    return path


def inventory(cfg: Config, corpus: Corpus) -> list[tuple[str, str, str | None, int]]:
    """What is in the corpus and how many chunks each source has indexed."""
    from qdrant_client import models

    client = index.connect(cfg)
    rows = []
    with State(cfg.storage.state_db):
        for src in _sources(cfg, corpus):
            try:
                n = client.count(
                    cfg.storage.collection,
                    count_filter=models.Filter(
                        must=[models.FieldCondition(key="source", match=models.MatchValue(value=src.rel))]
                    ),
                    exact=True,
                ).count
            except Exception:  # noqa: BLE001 - collection may not exist yet
                n = 0
            rows.append((src.rel, src.type, src.module, n))
    return rows

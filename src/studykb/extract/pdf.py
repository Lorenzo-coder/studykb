"""PDF -> Units, one per page.

Page boundaries are kept because the page number *is* the locator: every answer
built on a book chunk can tell you which page to open. Formulas survive as
approximate text, which is fine for finding the passage and not meant for
reading the maths.
"""

from __future__ import annotations

import re
import warnings
from collections import Counter
from pathlib import Path

from ..types import Unit

_HEADING = re.compile(r"^#{1,4} +(.+)$", re.MULTILINE)

# A line repeated on at least this share of pages is furniture: a running
# header, a page number, a copyright footer, a watermark.
_BOILERPLATE_SHARE = 0.6


def extract(path: Path) -> list[Unit]:
    import pymupdf4llm

    # pymupdf's layout heuristics divide by zero on zero-width spans, which many
    # of these PDFs contain. The warning is per-span and drowns the run log.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=RuntimeWarning, module="pymupdf")
        pages = pymupdf4llm.to_markdown(str(path), page_chunks=True, show_progress=False)

    graphics = _graphics_per_page(path)
    units: list[Unit] = []
    for page in pages:
        text = (page.get("text") or "").strip()
        page_no = page.get("metadata", {}).get("page", len(units) + 1)
        headings = _HEADING.findall(text)
        units.append(
            Unit(
                locator=f"p.{page_no}",
                text=text,
                provenance="text-layer",
                heading=headings[0].strip() if headings else "",
                # Vector drawings count as much as bitmaps: decks flattened by
                # tools like iLovePDF carry every diagram as vector art, and
                # missing that means the page is never sent for captioning.
                has_images=bool(page.get("images")) or graphics.get(page_no, 0) > 0,
                graphics=graphics.get(page_no, 0),
                page_no=page_no,
            )
        )
    return units


def _graphics_per_page(path: Path) -> dict[int, int]:
    import pymupdf

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        with pymupdf.open(path) as doc:
            return {
                i + 1: len(doc[i].get_images()) + len(doc[i].get_drawings())
                for i in range(doc.page_count)
            }


def text_layer_stats(path: Path) -> tuple[int, float]:
    """(page count, mean characters of *real* text per page).

    Boilerplate is subtracted first. A deck whose every page carries an
    identical copyright footer has a text layer on paper and none in practice;
    counting those characters is how a 137-page slide deck silently produced
    zero chunks.

    ponytail: exact-line matching, so a footer with a page number in it is not
    caught. Normalise digits here if that shows up.
    """
    import pymupdf

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        with pymupdf.open(path) as doc:
            n = doc.page_count
            if n == 0:
                return 0, 0.0
            per_page = [
                [line.strip() for line in doc[i].get_text().splitlines() if line.strip()]
                for i in range(n)
            ]

    seen = Counter(line for lines in per_page for line in set(lines))
    boilerplate = {line for line, count in seen.items() if count >= max(2, n * _BOILERPLATE_SHARE)}
    total = sum(len(line) for lines in per_page for line in lines if line not in boilerplate)
    return n, total / n

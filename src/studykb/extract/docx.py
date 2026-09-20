"""Word transcripts -> Units, one per time window.

The lectures are recorded by the platform and exported as Word documents, not
as caption files. A ``.docx`` (or ``.docm``, the same container with macros
allowed) is a zip holding its text in ``word/document.xml``, so reading one
needs no dependency: paragraphs are ``<w:p>`` elements and a paragraph's text
is the ``<w:t>`` runs inside it, concatenated.

Teams puts the speaker and the wall-clock time on a line of their own —
``[Calogero Zarbo] 14:05:04`` — and that time becomes the locator, for the
reason ``vtt`` gives: a passage that cannot send you back to the minute of the
recording is worth much less than one that can. The speaker's name is kept in
the text, because who said a thing is part of what it is worth.

Some transcripts are cleaned into continuous prose with every mark removed.
Those get a paragraph range instead, which is still a locator you can find the
passage by.

Either way the unit has to be bounded **here**: chunking never splits a
transcript window, and on this corpus the marks are not evenly spread. One file
carries all its timestamps in the last twenty minutes, so everything before the
first one lands in a single window — 100k characters, one chunk, unsearchable.
A window past the budget is therefore cut, and the pieces after the first say so
in their locator: ``@09:08:29 (2)``. The time is still the time the window
opened, which is the honest thing to cite when nothing finer was recorded.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from ..chunk import CHARS_PER_TOKEN
from ..config import Config
from ..types import Unit
from .vtt import _hhmmss, _seconds

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# "[Calogero Zarbo 00] 14:05:04", or a bare "09:08:44", alone on its paragraph.
# Anchored on both ends on purpose: body text says "it's 9:05" and that is not
# a mark.
_MARK = re.compile(r"^(?:\[(?P<who>[^\]]*)\]\s*)?(?P<t>\d{1,2}:\d{2}:\d{2})$")


def extract(path: Path, cfg: Config) -> list[Unit]:
    paragraphs = _paragraphs(path)
    budget = cfg.chunk.target_tokens * CHARS_PER_TOKEN
    if any(_MARK.match(p) for p in paragraphs):
        return _by_time(paragraphs, cfg.transcript.window_seconds, budget)
    return _by_paragraph(paragraphs, budget)


def _paragraphs(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as z:
        root = ElementTree.fromstring(z.read("word/document.xml"))
    # Runs join with no separator: Word splits a single word across runs
    # wherever formatting or a spell-check boundary falls, and the spaces are
    # already inside the run text.
    out = ("".join(t.text or "" for t in p.iter(f"{_W}t")).strip() for p in root.iter(f"{_W}p"))
    return [p for p in out if p]


def _by_time(paragraphs: list[str], window: int, budget: int) -> list[Unit]:
    units: list[Unit] = []
    buf: list[str] = []
    start: float | None = None

    for par in paragraphs:
        mark = _MARK.match(par)
        if not mark:
            buf.append(par)
            continue
        t = _seconds(mark["t"])
        if start is None:
            start = t
        elif t - start >= window and buf:
            units += _emit(f"@{_hhmmss(start)}", buf, budget, {"start_s": start})
            buf, start = [], t
        if mark["who"]:
            buf.append(f"[{mark['who']}]")

    if buf and start is not None:
        units += _emit(f"@{_hhmmss(start)}", buf, budget, {"start_s": start})
    return units


def _by_paragraph(paragraphs: list[str], budget: int) -> list[Unit]:
    units: list[Unit] = []
    buf: list[str] = []
    first = 1
    for i, par in enumerate(paragraphs, start=1):
        buf.append(par)
        if sum(map(len, buf)) >= budget:
            units += _emit(f"¶{first}-{i}", buf, budget)
            buf, first = [], i + 1
    if buf:
        units += _emit(f"¶{first}-{len(paragraphs)}", buf, budget)
    return units


def _emit(locator: str, lines: list[str], budget: int, extra: dict | None = None) -> list[Unit]:
    """One unit, or several when the window ran past the budget."""
    return [
        Unit(
            locator=locator if n == 0 else f"{locator} ({n + 1})",
            text=piece,
            provenance="asr",
            extra=extra or {},
        )
        for n, piece in enumerate(_cut(" ".join(lines), budget))
    ]


def _cut(text: str, budget: int) -> list[str]:
    """Break at the last space before the budget: a piece that starts mid-word
    is a worse retrieval hit than one that starts a sentence late."""
    pieces = []
    while len(text) > budget:
        # rfind says -1 when the whole stretch holds no space — a wall of URLs,
        # a pasted blob. Cutting at -1 would shorten the text by one character
        # per pass and never finish.
        at = text.rfind(" ", budget // 2, budget)
        at = budget if at <= 0 else at
        pieces.append(text[:at].strip())
        text = text[at:].lstrip()
    pieces.append(text.strip())
    return pieces

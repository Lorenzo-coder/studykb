"""Shared data model.

A source is extracted into ``Unit``s — one page, one slide, one transcript
window — which are then split into ``Chunk``s for indexing. Both carry a
``locator`` and a ``provenance``, and those two fields are what make the whole
system trustworthy:

* ``locator`` sends you to the exact page or the exact minute of the recording;
* ``provenance`` says whether the text was read from the file, guessed by OCR,
  described by a vision model or corrected from captions.

A local 7B VLM does not reliably transcribe a quantum circuit or a dense
derivation. Its output is a searchable description, not a source, and
``provenance`` is how that stays visible downstream.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

Provenance = Literal["text-layer", "ocr", "local-vlm", "asr", "asr-corrected"]
SourceType = Literal["book", "slides", "paper", "transcript", "code"]


@dataclass
class Unit:
    locator: str                       # "p.142" | "slide 7" | "2026-10-12 @00:34:12"
    text: str
    provenance: Provenance = "text-layer"
    heading: str = ""
    # Vision/OCR triggers need these; they are not indexed.
    char_count: int = 0
    # Vector ops + bitmaps on the page. A cover has ~1, a blank page 0, a real
    # figure page dozens — which is why this is a count and not a flag.
    graphics: int = 0
    page_no: int | None = None
    extra: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.char_count:
            self.char_count = len(self.text.strip())


@dataclass
class Chunk:
    id: str
    text: str
    source: str                        # path relative to the corpus root
    source_title: str
    type: SourceType | Literal["caption"]
    locator: str
    provenance: Provenance
    module: str | None = None
    heading: str = ""

    def payload(self) -> dict:
        """Everything but the id, which is already the Qdrant point id."""
        return {k: v for k, v in asdict(self).items() if k != "id"}

"""Units -> Chunks.

Splitting is deliberately dumb: paragraph-aware, heading-aware, no semantic
segmentation model. The locator is preserved through the split, which is what
retrieval quality actually rests on here.

Transcript windows are already the right size (five minutes of speech), so they
pass through whole — splitting them would sever the timestamp from part of its
own text.
"""

from __future__ import annotations

import re

from .config import ChunkCfg
from .state import chunk_id
from .types import Chunk, SourceType, Unit

_HEADING = re.compile(r"^(#{1,4} .+)$", re.MULTILINE)

# Character-per-token estimate. A real tokenizer would add a dependency and a
# model download to make a chunk boundary marginally better placed.
CHARS_PER_TOKEN = 4


def _split(text: str, cfg: ChunkCfg) -> list[str]:
    target = cfg.target_tokens * CHARS_PER_TOKEN
    overlap = cfg.overlap_tokens * CHARS_PER_TOKEN
    if len(text) <= target:
        return [text]

    blocks = _HEADING.split(text) if cfg.split_on == "headings" else [text]
    pieces: list[str] = []
    for block in blocks:
        pieces.extend(p for p in block.split("\n\n") if p.strip())

    out: list[str] = []
    buf = ""
    for piece in pieces:
        if buf and len(buf) + len(piece) + 2 > target:
            out.append(buf.strip())
            buf = (buf[-overlap:] + "\n\n") if overlap else ""
        buf += piece + "\n\n"
        # A single paragraph longer than the target (dense page, no blank lines)
        # still has to be cut, or one chunk swallows the whole page.
        while len(buf) > target * 1.5:
            out.append(buf[:target].strip())
            buf = buf[target - overlap :]
    if buf.strip():
        out.append(buf.strip())
    return out


def to_chunks(
    units: list[Unit],
    *,
    source: str,
    source_title: str,
    type_: SourceType | str,
    module: str | None,
    cfg: ChunkCfg,
    authority: str = "course",
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for unit in units:
        text = unit.text.strip()
        if not text:
            continue
        parts = [text] if type_ in ("transcript", "caption") else _split(text, cfg)
        for i, part in enumerate(parts):
            if not part.strip():
                continue
            chunks.append(
                Chunk(
                    id=chunk_id(source, unit.locator, i, str(type_)),
                    text=part,
                    source=source,
                    source_title=source_title,
                    type=type_,  # type: ignore[arg-type]
                    locator=unit.locator,
                    provenance=unit.provenance,
                    module=module,
                    heading=unit.heading,
                    authority=authority,  # type: ignore[arg-type]
                )
            )
    return chunks

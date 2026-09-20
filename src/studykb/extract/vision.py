"""Caption the pages whose meaning lives in a figure.

Slides are the reason this stage exists: roughly 40% of a lecture deck carries
its content in a diagram, a plot or a circuit, and text extraction returns only
the title. A caption makes that page *findable*; it is not a transcription, and
it is stored with ``provenance: local-vlm`` so it can never be mistaken for one.

Rendering is capped at ``max_long_side_px``. Qwen2.5-VL uses dynamic
resolution, and a full-resolution slide inflates the visual token count until it
saturates 8 GB of VRAM.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from ..config import Config
from ..limits import VISION_ERROR_HEAD
from ..llm import LLM, strip_thinking
from ..types import Unit


def should_caption(unit: Unit, cfg: Config, mode: str) -> bool:
    v = cfg.extract.vision
    if not v.enabled or mode == "never" or unit.page_no is None:
        return False
    # The graphics floor applies even to `force`. Handed a cover or a blank
    # page, the model does not answer "nothing here" — it pattern-completes
    # from the title and describes a circuit that does not exist. Not sending
    # the page is the only reliable defence.
    if unit.graphics < v.min_graphics:
        return False
    return mode == "force" or unit.char_count < v.trigger_chars_per_page


def render_page(pdf: Path, page_no: int, cfg: Config, out_dir: Path) -> Path:
    import pymupdf

    out = out_dir / f"{pdf.stem}-p{page_no}.png"
    with pymupdf.open(pdf) as doc:
        page = doc[page_no - 1]
        long_side = max(page.rect.width, page.rect.height)
        # Honour the DPI setting, but never exceed the VRAM-safe pixel ceiling.
        zoom = min(
            cfg.extract.vision.render_dpi / 72.0,
            cfg.models.vlm.max_long_side_px / long_side,
        )
        page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).save(out)
    return out


def caption_pages(pdf: Path, units: list[Unit], cfg: Config, llm: LLM, prompt: str, mode: str) -> list[Unit]:
    """Return caption Units for the pages that need one. Input units are untouched."""
    targets = [u for u in units if should_caption(u, cfg, mode)]
    if not targets:
        return []

    captions: list[Unit] = []
    with tempfile.TemporaryDirectory() as tmp:
        for unit in targets:
            assert unit.page_no is not None
            png = render_page(pdf, unit.page_no, cfg, Path(tmp))
            try:
                text = strip_thinking(llm.describe_image(png, prompt))
            except Exception as exc:  # noqa: BLE001 - one bad page must not sink the run
                captions.append(
                    Unit(
                        locator=unit.locator,
                        text="",
                        provenance="local-vlm",
                        extra={"error": str(exc)[:VISION_ERROR_HEAD]},
                        page_no=unit.page_no,
                    )
                )
                continue
            if text:
                captions.append(
                    Unit(
                        locator=unit.locator,
                        text=text,
                        provenance="local-vlm",
                        heading=unit.heading,
                        page_no=unit.page_no,
                    )
                )
    return [c for c in captions if c.text]

"""OCR for PDFs that arrive without a text layer.

Writes an OCR'd *copy* under the state directory and leaves the original
untouched, so the corpus stays mounted read-only. These are the user's only
copies of some of this material; a pipeline that rewrites them in place is one
bad ocrmypdf run away from losing a book.

Triggered by measured characters-per-page, never by guessing from the filename:
the corpus is still being downloaded and scanned handouts may arrive at any
time.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ..config import Config
from .pdf import text_layer_stats


def needs_ocr(path: Path, cfg: Config) -> bool:
    if not cfg.extract.ocr.enabled or path.suffix.lower() != ".pdf":
        return False
    pages, mean_chars = text_layer_stats(path)
    return pages > 0 and mean_chars < cfg.extract.ocr.trigger_chars_per_page


def run_ocr(path: Path, out: Path, cfg: Config) -> Path:
    """Write an OCR'd copy of `path` to `out`. Raises rather than indexing nothing."""
    if shutil.which(cfg.extract.ocr.cmd[0]) is None:
        raise RuntimeError(
            f"{cfg.extract.ocr.cmd[0]} not found. It ships in the studykb image; "
            f"outside the container install it or set extract.ocr.enabled: false."
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".partial.pdf")
    proc = subprocess.run(
        [*cfg.extract.ocr.cmd, str(path), str(tmp)],
        capture_output=True,
        text=True,
        timeout=cfg.extract.ocr.timeout_s,
    )
    # 6 = "already has text", which --skip-text turns into a success for us.
    if proc.returncode not in (0, 6) or not tmp.exists():
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"ocrmypdf failed on {path.name} ({proc.returncode}): {proc.stderr[-500:]}")
    tmp.replace(out)   # atomic: a killed run never leaves a half-written PDF behind
    return out

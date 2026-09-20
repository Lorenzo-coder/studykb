"""Extraction dispatch: file -> Units, by extension."""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..types import Unit
from . import asr, code, ocr, pdf, pptx, vtt, vision

__all__ = ["asr", "code", "ocr", "pdf", "pptx", "vtt", "vision", "extract_units", "SUPPORTED"]

SUPPORTED = {".pdf", ".pptx", ".vtt", ".srt", ".ipynb", ".py"}


def extract_units(path: Path, cfg: Config) -> list[Unit]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return pdf.extract(path)
    if suffix == ".pptx":
        return pptx.extract(path)
    if suffix in (".vtt", ".srt"):
        return vtt.extract(path, cfg)
    if suffix == ".ipynb":
        return code.extract_notebook(path, cfg)
    if suffix == ".py":
        return code.extract_python(path)
    raise ValueError(f"no extractor for {suffix} ({path.name})")

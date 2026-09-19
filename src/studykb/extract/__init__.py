"""Extraction dispatch: file -> Units, by extension."""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..types import Unit
from . import asr, ocr, pdf, pptx, vtt, vision

__all__ = ["asr", "ocr", "pdf", "pptx", "vtt", "vision", "extract_units", "SUPPORTED"]

SUPPORTED = {".pdf", ".pptx", ".vtt", ".srt"}


def extract_units(path: Path, cfg: Config) -> list[Unit]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return pdf.extract(path)
    if suffix == ".pptx":
        return pptx.extract(path)
    if suffix in (".vtt", ".srt"):
        return vtt.extract(path, cfg)
    raise ValueError(f"no extractor for {suffix} ({path.name})")

"""Caption files -> Units, one per time window.

Timestamps are the whole point: a transcript chunk that cannot send you back to
the minute of the recording is worth much less than one that can. Captions are
grouped into windows of ``transcript.window_seconds`` and the window's start
time becomes the locator.
"""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..types import Unit


def _seconds(stamp: str) -> float:
    """'00:34:12.500' or '00:34:12,500' -> 2052.5"""
    h, m, s = stamp.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def _hhmmss(total: float) -> str:
    t = int(total)
    return f"{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}"


def extract(path: Path, cfg: Config) -> list[Unit]:
    import webvtt

    captions = (
        webvtt.from_srt(str(path)) if path.suffix.lower() == ".srt" else webvtt.read(str(path))
    )

    window = cfg.transcript.window_seconds
    units: list[Unit] = []
    buf: list[str] = []
    start: float | None = None
    last_line = ""

    for cap in captions:
        text = " ".join(cap.text.split())
        # Rolling captions repeat the previous line as they scroll; keeping the
        # duplicates would triple the token count for no extra information.
        if not text or text == last_line:
            continue
        last_line = text
        t = _seconds(cap.start)
        if start is None:
            start = t
        if t - start >= window and buf:
            units.append(_unit(start, buf))
            buf, start = [], t
        buf.append(text)

    if buf and start is not None:
        units.append(_unit(start, buf))
    return units


def _unit(start: float, lines: list[str]) -> Unit:
    return Unit(
        locator=f"@{_hhmmss(start)}",
        text=" ".join(lines),
        provenance="asr",
        extra={"start_s": start},
    )

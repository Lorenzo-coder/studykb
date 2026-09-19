"""Repair auto-generated captions with a local model.

The course is taught in non-native English, so the platform's ASR mangles proper
nouns and technical terms — and a lexical search over "cubit annealing" finds
nothing. Each window is passed to the local text model together with a glossary
built from the calendar (lecture titles, teacher names) plus the corpus manifest.

Runs locally, so it costs an overnight batch and no money. The correction is
marked ``provenance: asr-corrected`` and the raw text is kept beside it: a model
that repairs terminology can also invent it.
"""

from __future__ import annotations

from ..llm import LLM, strip_thinking
from ..types import Unit

MAX_GROWTH = 1.35  # a "correction" longer than this is the model rambling


def correct(units: list[Unit], glossary: list[str], llm: LLM, prompt_tpl, lecture: str = "") -> list[Unit]:
    if not units:
        return []
    terms = ", ".join(sorted(set(glossary)))
    out: list[Unit] = []
    for unit in units:
        try:
            fixed = strip_thinking(
                llm.complete(prompt_tpl.render(glossary=terms, lecture=lecture, text=unit.text))
            )
        except Exception:  # noqa: BLE001 - a failed window keeps its raw text
            out.append(unit)
            continue

        if not fixed or len(fixed) > len(unit.text) * MAX_GROWTH:
            out.append(unit)
            continue

        out.append(
            Unit(
                locator=unit.locator,
                text=fixed,
                provenance="asr-corrected",
                heading=unit.heading,
                extra={**unit.extra, "raw": unit.text},
            )
        )
    return out

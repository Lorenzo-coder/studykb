"""Repair auto-generated captions with a local model.

The course is taught in non-native English, so the platform's ASR mangles proper
nouns and technical terms — and a lexical search over "cubit annealing" finds
nothing. Each window is passed to the local text model together with a glossary
built from the calendar (lecture titles, teacher names) plus the corpus manifest.

Runs locally, so it costs an overnight batch and no money. The correction is
marked ``provenance: asr-corrected`` and the raw text is kept beside it: a model
that repairs terminology can also invent it.

Two kinds of window never reach the model. A Word transcript already cleaned
into prose carries a paragraph-range locator (``¶12-40``, see ``docx``): it is
written text, not captions, and on the QML corpus the "cleanup" only damaged it
— summaries, unrelated answers, the prompt echoed back. And a correction is
dropped when it changes more than a tenth of the words: fixing "cue bit" moves a
few tokens, anything past that is a rewrite.
"""

from __future__ import annotations

import re
from dataclasses import replace
from difflib import SequenceMatcher

from ..llm import LLM, strip_thinking
from ..types import Unit

# Word overlap a correction must keep with its input, punctuation and case
# ignored. Measured on 276 corrected windows: every leaked prompt or unrelated
# answer but one scored under 0.9; the one at 0.95 is also caught by the marker
# list below.
MIN_SIMILARITY = 0.9
# Phrases the model writes when it talks about the task instead of doing it.
_LEAKS = re.compile(r"you are given a text|corrected text|key corrections|it seems like your", re.I)


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _words(a), _words(b), autojunk=False).ratio()


def is_prose(unit: Unit) -> bool:
    return unit.locator.startswith("¶")


def correct(units: list[Unit], glossary: list[str], llm: LLM, prompt_tpl, lecture: str = "") -> list[Unit]:
    if not units:
        return []
    terms = ", ".join(sorted(set(glossary)))
    out: list[Unit] = []
    for unit in units:
        if is_prose(unit):
            out.append(replace(unit, provenance="text-layer"))
            continue
        try:
            fixed = strip_thinking(
                llm.complete(prompt_tpl.render(glossary=terms, lecture=lecture, text=unit.text))
            )
        except Exception:  # noqa: BLE001 - a failed window keeps its raw text
            out.append(unit)
            continue

        if not fixed or _LEAKS.search(fixed) or _similarity(unit.text, fixed) < MIN_SIMILARITY:
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

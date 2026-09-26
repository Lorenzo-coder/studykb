"""ASR cleanup must repair captions and never replace them.

The model answers below are real: they are what qwen3:8b returned for lecture
windows of the QML corpus on 22 September.
"""

from __future__ import annotations

from studykb.extract.asr import correct
from studykb.llm import strip_thinking
from studykb.types import Unit

RAW = (
    "so the cue bit is in superposition and when we apply the hadamard gate on the first cue bit "
    "we get the plus state then the c not entangles it with the second one and this is the bell state "
    "that we saw last week with professor caruso when we talked about the density matrix"
)
FIXED = RAW.replace("cue bit", "qubit").replace("c not", "CNOT").replace("caruso", "Caruso")


class Tpl:
    def render(self, **kw) -> str:
        return kw["text"]


class Canned:
    def __init__(self, answer: str):
        self.answer, self.calls = answer, 0

    def complete(self, prompt: str) -> str:
        self.calls += 1
        return self.answer


def _run(answer: str, locator: str = "@09:08:29") -> tuple[Unit, Canned]:
    llm = Canned(answer)
    (out,) = correct([Unit(locator=locator, text=RAW, provenance="asr")], [], llm, Tpl())
    return out, llm


def test_a_real_correction_is_kept_without_the_think_switch():
    out, _ = _run(FIXED + " /think")
    assert out.provenance == "asr-corrected"
    assert out.text == FIXED
    assert out.extra["raw"] == RAW


def test_an_unrelated_answer_keeps_the_raw_window():
    out, _ = _run(
        "To determine the number of ways to arrange items, we need to consider the specific "
        "constraints or conditions of the problem. ### 1. **Permutations of Distinct Items**"
    )
    assert (out.text, out.provenance) == (RAW, "asr")


def test_the_prompt_echoed_back_keeps_the_raw_window():
    out, _ = _run("It seems like your message got cut off or there was an error in the input.")
    assert out.text == RAW


def test_a_leak_around_an_otherwise_faithful_text_is_rejected():
    out, _ = _run("Corrected Text: " + FIXED)
    assert out.text == RAW


def test_cleaned_prose_never_reaches_the_model():
    out, llm = _run("anything", locator="¶46-89")
    assert llm.calls == 0
    assert (out.text, out.provenance) == (RAW, "text-layer")


def test_strip_thinking_leaves_a_mid_sentence_slash_alone():
    assert strip_thinking("<think>x</think> use /think only at the end /no_think") == "use /think only at the end"

# Enrichment: vision and ASR

`src/studykb/extract/vision.py` and `extract/asr.py`

Two stages that **generate** text rather than reading it. Both mark their output
with a [provenance](../glossary.md#provenance) that says so, because generated
text sitting next to source text in the same index is otherwise indistinguishable.

---

## Vision captioning

Slide decks carry a large share of their meaning in diagrams, circuits and
plots. Text extraction returns the title and nothing else. A caption makes that
page **findable**; it is not a transcription.

### When a page is sent

`should_caption(unit, cfg, mode)`:

```python
if not enabled or mode == "never" or unit.page_no is None:  return False
if unit.graphics < cfg.extract.vision.min_graphics:         return False   # 12
return mode == "force" or unit.char_count < cfg.extract.vision.trigger_chars_per_page
```

The graphics floor applies **even under `force`**, and that is the important
line. Handed a cover page, a 7B vision model does not answer "this is a cover" —
it pattern-completes from the title. Page 1 of Nielsen & Chuang came back as *"a
circuit diagram with qubits labelled A, B, C, a Hadamard gate and a table
below"*. That page is the front cover. Not sending the page is the only defence
that works; the prompt alone is not enough, though it also names the cover case
now.

### Why prose is excluded

`vision: never` on books and papers, set in `corpus.yaml`. Measured, not assumed:

- the `auto` trigger fires on low-text pages, and in a book those are covers,
  title pages and blanks — real figures sit on pages surrounded by text and were
  never sent;
- on the pages it did reach, the model fabricated.

Fabricated text in the index is worse than absent text, because provenance is a
tag most readers skim past. Slides keep `vision: force`: there the content
genuinely is the figure, and the captions come back accurate — verified by hand
against the rendered page.

### Rendering

```python
zoom = min(dpi / 72, max_long_side_px / long_side)
```

The pixel ceiling is not cosmetic. Qwen2.5-VL uses dynamic resolution, and a
full-resolution slide inflates the visual token count until it saturates 8 GB of
VRAM. At 1280 px on the long side the model sits at about 6.8 GB of 8 GB.

`caption_pages` falls back to the smaller `granite3.2-vision:2b` when the 7B
model fails on a page, so a dense slide yields a weaker caption rather than
none.

---

## ASR cleanup

The course is taught in non-native English. Automatic captions mangle proper
nouns and technical terms, and lexical search over "cue bit annealing" finds
nothing.

`correct()` passes each window to the local text model together with a glossary
assembled from two sources: the terms listed in `corpus.yaml`, and the lecture
titles and teacher names parsed out of the timetable
([calendar.md](calendar.md)). Those are precisely the words ASR gets wrong.

Guards, because a model that repairs terminology can also invent it:

```python
if is_prose(unit):                       # locator "¶12-40": already written text
    keep it, provenance text-layer, no model call
if not fixed or _LEAKS.search(fixed) or _similarity(unit.text, fixed) < MIN_SIMILARITY:  # 0.9
    out.append(unit)                     # keep the raw window
```

`_similarity` is the word overlap with punctuation and case ignored. Fixing
"cue bit" changes a few words; a summary, an answer about something else, or
the prompt echoed back changes most of them. `_LEAKS` catches the model talking
about the task ("Corrected Text:") when the rest is faithful. The raw text is
kept in `extra["raw"]` next to every accepted correction.

Output carries `provenance: asr-corrected`.

### What the first run did (26 September)

Every QML transcript is a Word file already cleaned into prose, so the stage had
nothing to repair. It still changed 276 of 331 windows. About 40 were damaged:
summaries, unrelated answers (combinatorics in a lecture on neutral atoms),
the prompt echoed back. Terms were also "corrected" wrongly: neuron → qubit,
Pasqal → Pasquale. And 89 ended in a stray `/think`. Since then prose windows
skip the model, and the guards above apply to real captions.

---

## Gate

```bash
uv run studykb review --corpus <name> --what captions
```

`captions.md` places each rendered page image directly above what the model said
about it. Read down; a fabricated diagram is obvious in a second. The report also
names every source that produced no captions **and why** — captioning off for
prose, no page above the graphics floor, vision not run yet — because an
unexplained absence reads as a failure.

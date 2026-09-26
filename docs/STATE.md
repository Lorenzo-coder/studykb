# Where this is right now

Last updated: 2026-09-26 (authority split, QBoost and two M7 decks indexed). Read this first when resuming.

> **Next session — agreed, ready to start.** Jump to [Next session](#next-session).

## The one-paragraph version

studykb is built and verified against the real corpus: 15 sources, ~4,250 pages,
3,544 chunks, citations checked by hand. The review pipeline that validates the
data is complete and its five checks are green on the test corpus. What does not
exist is everything around it — backup, scheduling, CI. Two capabilities are
written but have never run because the material is missing: OCR needs a scanned
PDF, ASR cleanup needs lecture captions.

## The corpus is indexed

**22 September:** 148 sources, **7,446 chunks**, all five review checks green.
The 29 transcripts are in — Word write-ups, one per lesson, placed by the
lecturer on their first line (M1, M4-M7; see MANIFEST.md). 55 of their 331
chunks kept the raw text because the ASR repair failed its length guard. Ten
new papers, two of them renames of indexed files. Every ingest now writes
`vault/SOURCES.md`, the per-file list by module, and `search --source` narrows
a query to one file.

The run below is the first full index, 20 September.

Run `2cf6ed7c08a8`, 20 September. 116 sources, **6,913 chunks**, no errors, and
all five review checks green.

| stage | time | sources | items | per item | Wh | peak W |
|---|---|---|---|---|---|---|
| extract | 16m12s | 116 | 116 | 8.4s | 5.6 | 21 |
| vision | 46m50s | 33 | 731 captions | 3.8s | 77.8 | 129 |
| embed | 3m54s | 116 | 6,913 chunks | 2.0s | 5.9 | 141 |
| **total** | **1h06m** | | | | **89.3** | |

1.2M tokens into the vision model, 2.9M into the embedder. The estimate before
the run was 30-40 minutes and it was wrong by roughly half: captioning a dense
lecture slide takes 3.8s, not the 1.8s measured on a sparse handwritten page,
and 16 minutes of CPU extraction over 2,000+ pages had not been counted at all.

Checks:

```
✅ every source is indexed
✅ nothing was lost on the way in — 6913 produced, 6913 in the collection
✅ no page with text was dropped
✅ prose chunks are worth indexing — 105 of 4232 under 200 chars (2.5%)
✅ captions carry content — 731 captions, 57 trivial (7.8%)
```

Retrieval verified by hand: `-m M3` returns Droghetti's notes, `--type code`
returns GroverTutorial with cell-range locators, and a plain query for
backpropagation returns Ligorio's M2 deck at p.37.

**Still missing: M8 lectures.** It has two papers and nothing else.

## FCaruso: handwriting, not a scan

`FCaruso_From Quantum Computing to Quantum AI_2026.pdf` is 137 pages with **zero
characters of text**, which is why the OCR trigger fires on it. It is not a scan.
It is a lecture written by hand on a tablet: 48-370 vector strokes per page,
median 167.

**ocrmypdf cannot read it and must not be run on it.** tesseract is trained on
printed type; handwriting is a different task it was never built for. Worse, OCR
output is extracted as `provenance: text-layer` — the most trusted label — so a
run would index tesseract's guesses as if they had been read from the file.

The vision model handles it. Measured on this machine with `qwen2.5vl:7b`:

| page | result |
|---|---|
| p30 — formulas only, no words | `"Blank page."` — total failure |
| p75 — words, colour, boxes | title, keywords and the claim, all correct |
| 8 pages sampled across the deck | 8/8 produced usable content |

One failure in ten pages tried. 1.8 s per page, so ~4 minutes for all 137.

The limit is exactly the one `provenance: local-vlm` already states: it reads the
**words**, it gets the **formulas wrong**. On p75 it emitted `O(W) → O(W)` where
the page says `O(N) → O(√N)`. Good for finding the page, never for quoting it.

Without this stage those 137 pages are invisible to search. Keep `type: slides`
in MANIFEST.md, which forces captioning regardless of any other threshold.

## Blocked on material, not code

| what | needed for | where to get it |
|---|---|---|
| lecture captions (`.vtt`/`.srt`) | timestamped citations — the Word transcripts carry no timestamps | university platform — captions menu in Panopto, `.vtt` in devtools for Moodle/Kaltura, transcript export in Teams |
| slides for M5, M6, M7 | M5 and M7 have papers and books, but no slides at all; M6 has nothing | ask the teachers while the contact is warm; M7 ended 26 Sep |
| material for M1, M6, M8 | those three are the real gaps: **zero sources each**, and M8 is the 8-CFU module | Corazza teaches the first lecture, 12 Oct |
| one scanned PDF of **printed** text | exercising the OCR path even once | anything image-only — handwriting does not count, tesseract cannot read it |

## Decisions already made

- **Framework guides are not captioned** (26 September). Qiskit, PennyLane,
  D-Wave and Pulser guides printed from the web (24 PDFs, M5-M7) have a full
  text layer, so no OCR. A vision pilot on one PennyLane demo produced captions
  that only restated the text or the code; the rule was removed (see
  `corpus.yaml`). Fixed on the way: `_chunks_for` re-indexed a captions file
  even after vision was switched off for the source; it now reads captions only
  when the vision stage applies. Test: `test_captions_left_behind_by_a_vision_rule_are_not_indexed`.

- **ASR cleanup skips cleaned prose** (26 September). Every QML transcript is a
  Word report already written as prose; the cleanup model damaged about 40 of
  331 windows and swapped terms in many more. Prose windows (`¶` locators) now
  pass through as `text-layer`; real captions keep the model, behind a word
  similarity guard. Details in `docs/internals/enrichment.md`. The transcripts
  were re-embedded the same day and the notes citing them reviewed.

| | |
|---|---|
| Package manager | uv, everywhere, including the Dockerfile. Never pip |
| Docs language | English |
| Docs depth | one per subsystem plus a glossary |
| Roadmap scope | platform + operations, not the study workflow |
| Skills | `skills/` holds them for versioning only — nothing loads them from here, they are symlinked into `~/Personale/.claude/skills/`. See `skills/README.md` |
| Repo | `/home/locode/Personale/studykb` → `git@github.com:Lorenzo-coder/studykb.git`, private. Pushed over SSH; `gh` is still not installed |
| Vision | slides only; measured net-negative on prose |
| Models | local first: bge-m3, qwen2.5vl:7b, granite3.2-vision:2b, qwen3:8b |
| Where a number lives | three places, by what it changes — see below |
| Reading the notes | `GET /read` on the serve process, KaTeX in the browser. The terminal is for the dialogue, the browser for the reading |

## One state file per machine, and there are two of them

The file that records what has already been processed lives in a different place
depending on how the command is launched:

| launched as | state | extractions |
|---|---|---|
| `uv run studykb ...` | `.cache/state-<domain>.db` | `.cache/work/` |
| `docker compose run ...` | the `studykb_state` volume | the same volume |

Everything so far was run from the host; the container volume is **empty**.

They are not interchangeable. `studykb review` reads the extracted units from
`cfg.work`, so ingesting in the container and reviewing on the host reports every
source as "not extracted" — two directories, not a bug.

**Stay on the host.** The only thing the container was needed for was ocrmypdf,
and the file that wanted it turned out to be handwriting, which ocrmypdf cannot
read anyway.

## What a run costs

Every stage writes one row into `state.db`: wall time, sources, items, model
calls, tokens, and watt-hours integrated from `nvidia-smi` while it ran.
`ingest` prints the table when it finishes; `studykb stats` compares it against
previous runs. See [metrics.md](internals/metrics.md).

The figure is whole-GPU draw, not this process's share, and it excludes the
CPU — which is why `extract`, pure CPU work, reads 5.6 Wh at an idle 21 W over
sixteen minutes. The real run is in [The corpus is indexed](#the-corpus-is-indexed).

Compare `per item` between runs, never total time: the corpus grows.

## Where to change a number

Nothing tunable is buried in a function any more. A value lives in exactly one
of three places, chosen by what changing it does:

| place | what it holds | example |
|---|---|---|
| `config/default.yaml` | what gets indexed, and what a review check decides | `min_graphics`, `chunk.target_tokens`, `review.tiny_chunk_chars` |
| `src/studykb/limits.py` | how much a report prints before it truncates | `VANISHED_LISTED`, `RETRIEVAL_PASSAGE` |
| a constant at the top of its module | one value used only there | `CHARS_PER_TOKEN`, `MIN_SIMILARITY`, `_BOILERPLATE_SHARE` |

The last section of `limits.py` is fenced off: `FINGERPRINT_CHARS`,
`WORK_SHA_CHARS`, `WORK_STEM_CHARS` are key lengths already written into
`state.db` and into filenames. Changing one reruns every stage of every source.

## Corpus restructure, in progress

The corpus root is being reorganised into `<type>/M<n>/`, which lets the
`path_regex` rule assign the module and empties most of MANIFEST.md.

Three things to fix before the next ingest, found by walking the tree:

1. `Calendario_MasterQML_2526.xlsx` was moved into `burocracy/`. `corpus.yaml`
   looks for it at the root, so **there is currently no calendar**: no modules,
   no teachers, no syllabus pages, no glossary, and the date-based module rule
   silently stops resolving. It is not paperwork — it is the only syllabus this
   master has. Move it back.
2. `burocracy/` is not in `exclude`, and the per-filename patterns (`Bando *.pdf`
   and friends) anchor at the start of the path, so they no longer match now that
   the files moved into a folder. The catch-all `**/*.pdf` would index every
   invoice and enrolment form as a paper. Add `burocracy/**` and delete the
   twelve filename patterns it replaces.
3. `ML Notes_v1.pdf` is study material (M2) sitting in `burocracy/`.

Still unplaced: the 7 notebooks and `lect5_testing.pdf` at the top of `papers/`,
and the 9 books still in `Book/`. *(Done — see the corpus commits.)*

**Get the module right before ingesting.** A module is not part of the source
checksum or of any stage fingerprint, so correcting it in MANIFEST.md afterwards
does **not** trigger a re-index — the old module stays in the payload. Moving the
file instead makes a second source under the new path while the old chunks stay.
Either way the fix is `studykb forget <path>` and then re-ingest. Before the
first ingest it costs nothing.

## Notebooks and Python files

`.ipynb` and `.py` are not in `extract.SUPPORTED`, so they are skipped in silence
— no error, no line in the report.

The 7 notebooks under `papers/` are tutorials (PennyLane, Deutsch-Jozsa, Grover,
QGAN, Qiskit). Their markdown cells are prose worth indexing, and a notebook is
JSON, so an extractor is ~20 lines of stdlib with no new dependency: markdown
cells only, `cell N` as the locator, outputs discarded. **Not built yet.**

`pyhtonTest/` is **not thesis code** — corrected by its author. It is a past
exercise: a knapsack pipeline solving the same problem four ways (Pyomo/Gurobi
exact, QUBO, Qiskit QAOA, dimod annealing), first committed 14 March 2026, the
day of M1's "Introduction to Python" with Raffaele Pesenti. It lives outside the
corpus root; indexing it means symlinking the 9 files into `kb/code/`, which
keeps one copy on disk and stays current.

## Open, not decided

- **`enabled: false` does not drop chunks already indexed** — ingest should drop
  what the manifest disables; today it takes a `forget`. Found on the two
  `Assessment … Attempt review` PDFs, which were then re-enabled on purpose:
  they stay searchable (`-s Assessment`) with **no module**, since each covers
  three. The dry run's "2 sources with no module" is those two, expected.
- **Backup** (`DELIVERY.md` 5.1) — the highest-value gap. The vault cannot be
  regenerated by anything.
- The three gates that would close three 🟡: `selftest ocr`, `selftest serve`,
  `review --what syllabus`.
- Three test-corpus sources still have no module in `corpora/test/MANIFEST.md`,
  so the `-m` filter is untested.
- Thesis direction. `vault/20-thesis/shortlist.md` recommends preparing B
  (QUBO portfolio selection) and aiming for A (quantum diffusion for financial
  time series). An earlier version of this note said B would extend
  `QML/pyhtonTest`; that is wrong — the knapsack pipeline is a past exercise and
  nothing in the thesis builds on it. Neither option has a starting point yet.

## The date that governs everything

**16 October 2026** — the thesis project is *presented*, not started. In-person
teaching begins 12 October with Corazza and Fasano in the room; speak to them
before the 16th. Module 8 assessment is 7 November.

## Next session

Two pieces of work, both decided. Do them in this order.

### 1. Split the index by authority — done, 26 September

Every chunk carries `authority`: `reference` (books, papers) or `course`
(what was taught). It follows the type unless a `corpus.yaml` rule sets it:
the handouts, lecture notes, exercises, exam reviews and `ML Notes` filed
under `books/` and `papers/` are course. 25 sources reference, 133 course;
4,018 and 3,708 chunks.

`search -a reference|course`, the same argument on `kb_search`, and
`kb_crosscheck(topic)`, which runs both sides and labels them. Gate passed on
the real index: `kb_crosscheck("Grover")` returns the July assessment, Caruso
p.85 and GroverTutorial on the course side, Schuld p.140-141 and Nielsen &
Chuang on the reference side; `-a reference` returns only books and papers.

Run `587e1fe3cc3b`: 158 sources, **7,726 chunks**, 14m11s, review green. Only
embed re-ran on the old sources — the new field is in the embed fingerprint,
nothing upstream changed. Added in the same run: QBoost (4 code files from
`dwave-examples/qboost`, Neven 2008 and 2012), shown by Zarbo on 25/09, and
the M7 decks of 18/09 and 19/09.

### 2. Produce one module's notes as a format sample

Never done once. `vault/10-modules/` does not exist.

Pick one lecture from M4 (it has 972 chunks and real material), follow
`docs/agents/note-synthesis.md`, and produce the note. He reviews the **format**
before it is applied to anything else.

A worked example of the intended shape, from a live `kb_search` on M4:

> ### Grover's algorithm
> **The problem.** A search space of N items, no knowledge of how they are
> organised; find the one with a given property. [Nielsen & Chuang p.72]
> **The result.** Classically ~N operations; the quantum algorithm needs ~√N. [p.72]
> **Careful.** Quadratic speedup, not exponential. Shor is exponential, Grover is not. [p.72]

`papers/Quantum Machine Learning A Hands-on Tutorial…pdf`, a duplicate of the
copy in `books/`, was deleted from disk and forgotten from the index.

---

## Orientation

- [DELIVERY.md](DELIVERY.md) — what is built, missing, and how to validate each
- [README.md](README.md) — the documentation map
- [glossary.md](glossary.md) — read first if the terms are unfamiliar
- `git log --oneline` — every fix carries its reasoning in the commit message

# Where this is right now

Last updated: 2026-09-20 (second pass). Read this first when resuming.

> **Next session — agreed, ready to start.** Jump to [Next session](#next-session).

## The one-paragraph version

studykb is built and verified against the real corpus: 15 sources, ~4,250 pages,
3,544 chunks, citations checked by hand. The review pipeline that validates the
data is complete and its five checks are green on the test corpus. What does not
exist is everything around it — backup, scheduling, CI. Two capabilities are
written but have never run because the material is missing: OCR needs a scanned
PDF, ASR cleanup needs lecture captions.

## Pending work on the real corpus

`qml-master` has work queued from correctness fixes made after it was last
indexed. **Nothing has been run on it since**, on purpose.

```bash
uv run studykb ingest --corpus qml-master --root /home/locode/Personale/QML --dry-run
```

| stage | pending | why |
|---|---|---|
| `extract` | all 15 | the extract fingerprint is now the constant `v4`, so no source matches — see below |
| `vision` / `embed` | all | they gate on extract through `_UPSTREAM`, so they follow it |
| `ocr` | 0 | **switch it off** — the one file that triggered it is handwriting, see below |

`extract` went to `v4` when `Unit.has_images` was deleted: the field was written
by both extractors and read by nobody, but units JSON written by `v3` still
carries it, and `_load_units` does `Unit(**d)`, which rejects a key the class no
longer has. Bumping the fingerprint rewrites those files instead.

**So the next run must be a full one.** `--only` skips extract, leaves the old
JSON in place and crashes on it.

```bash
docker compose run --rm studykb ingest --corpus qml-master   # not --only
uv run studykb review --corpus qml-master --root /home/locode/Personale/QML
```

The 3,544 chunks already in Qdrant are intact and search works meanwhile.
Re-running costs about 15 minutes and fixes the 10 slide pages whose text a
caption overwrote.

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
| lecture captions (`.vtt`/`.srt`) | transcripts, ASR cleanup, timestamped citations | university platform — captions menu in Panopto, `.vtt` in devtools for Moodle/Kaltura, transcript export in Teams |
| slides for M5, M6, M7 | M5 and M7 have papers and books, but no slides at all; M6 has nothing | ask the teachers while the contact is warm; M7 ended 26 Sep |
| material for M1, M6, M8 | those three are the real gaps: **zero sources each**, and M8 is the 8-CFU module | Corazza teaches the first lecture, 12 Oct |
| one scanned PDF of **printed** text | exercising the OCR path even once | anything image-only — handwriting does not count, tesseract cannot read it |

## Decisions already made

| | |
|---|---|
| Package manager | uv, everywhere, including the Dockerfile. Never pip |
| Docs language | English |
| Docs depth | one per subsystem plus a glossary |
| Roadmap scope | platform + operations, not the study workflow |
| Repo | `/home/locode/Personale/studykb` → `git@github.com:Lorenzo-coder/studykb.git`, private. Pushed over SSH; `gh` is still not installed |
| Vision | slides only; measured net-negative on prose |
| Models | local first: bge-m3, qwen2.5vl:7b, granite3.2-vision:2b, qwen3:8b |
| Where a number lives | three places, by what it changes — see below |

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

## Where to change a number

Nothing tunable is buried in a function any more. A value lives in exactly one
of three places, chosen by what changing it does:

| place | what it holds | example |
|---|---|---|
| `config/default.yaml` | what gets indexed, and what a review check decides | `min_graphics`, `chunk.target_tokens`, `review.tiny_chunk_chars` |
| `src/studykb/limits.py` | how much a report prints before it truncates | `VANISHED_LISTED`, `RETRIEVAL_PASSAGE` |
| a constant at the top of its module | one value used only there | `CHARS_PER_TOKEN`, `MAX_GROWTH`, `_BOILERPLATE_SHARE` |

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
and the 9 books still in `Book/`.

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

### 1. Split the index by authority

**The problem.** Lecture material and reference material carry the same weight
in search results. A lecturer speaking off the cuff, and an automatic subtitle
on top of that, can be wrong. A textbook is not. And separately: knowing
whether a topic was *covered in the course* is what decides whether it is on
the exam.

**The design, agreed.** One index, not two. A new `authority` field on every
chunk:

| value | sources |
|---|---|
| `reference` | books, papers |
| `course` | slides, transcripts, captions |

**Slides count as `course`** — decided. They are written and reviewed, so more
reliable than a recording, but for the question "is this on the syllabus?" they
are course material.

Two separate collections were considered and rejected: two searches per
question, scores that cannot be ranked together, and every piece of
infrastructure doubled. The `type` field already separates the data; what is
missing is a single axis and a tool that compares across it.

**To build:**

1. `authority` on `SourceRule` in `config.py`, declared per glob in
   `corpus.yaml`, defaulting from the type (book/paper → reference, everything
   else → course).
2. Carry it into the chunk payload (`types.py::Chunk.payload`) and add it to
   `index.KEYWORD_FIELDS` so it can be filtered.
3. `--authority` on `studykb search`, and the same argument on `kb_search`.
4. A new MCP tool `kb_crosscheck(topic)`: searches both sides and returns them
   labelled, so an answer can read *"covered in the course on 29/05, slides
   23-27; the textbook confirms it at Nielsen & Chuang p.72"* — or *"not
   covered in the course; present in Schuld ch. 8, probably out of scope"*.
5. Bump the embed fingerprint: the payload changes, so everything reindexes
   (~15 min).

**Gate:** `kb_crosscheck("Grover")` must return both sides labelled correctly,
and `search --authority reference` must return no slides or transcripts.

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

### Also queued

The re-ingest described above — run it first, since both tasks need a current
index.

---

## Orientation

- [DELIVERY.md](DELIVERY.md) — what is built, missing, and how to validate each
- [README.md](README.md) — the documentation map
- [glossary.md](glossary.md) — read first if the terms are unfamiliar
- `git log --oneline` — every fix carries its reasoning in the commit message

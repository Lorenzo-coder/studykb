# Delivery roadmap

Every macro-capability the finished application needs, from zero. Application
capabilities, not algorithms: "can the system do X and can you tell that it
did X correctly", not "is the chunking strategy good".

**Each step has a gate**: a command that produces evidence you can judge before
moving on. A step is not done when the code runs — it is done when the gate is
green and you have looked at what it printed.

| | meaning |
|---|---|
| ✅ | built, gate exists, gate has been run against real material |
| 🟡 | built, but the gate has never exercised the real path |
| ⬜ | not built |

---

## Phase 1 — Runtime

### 1.1 Environment ✅

Docker with Compose v2, Qdrant, ollama on the host with the four models, the
Python environment via uv.

**Gate**
```bash
uv run studykb doctor
```
Exits non-zero if anything is missing. Every line must be ✓ except `ocrmypdf`,
which is expected to be missing outside the container.

### 1.2 Container image ✅

One image carrying the CLI, tesseract, ocrmypdf and poppler. Models stay on the
host, so no container needs the GPU.

**Gate**
```bash
docker compose build studykb && docker compose run --rm studykb doctor
```
Inside the container every line must be ✓, `ocrmypdf` included. Paths must read
`/vault` and `/data`, not host paths — if they read host paths, `config/local.yaml`
has leaked into the image and `.dockerignore` is wrong.

---

## Phase 2 — Getting material in

### 2.1 Corpus definition and discovery ✅

Globs find sources; exclude patterns drop the paperwork; module rules and
`MANIFEST.md` assign each file to a module. See
[discovery.md](internals/discovery.md).

**Gate**
```bash
uv run studykb ingest --corpus <name> --dry-run
```
Check three things: the source count matches what you expect, nothing from
another corpus or from `review/` appears, and the "sources with no module" list
is empty or expected.

### 2.2 Document intelligence — extraction ✅

PDF via pymupdf4llm with page boundaries preserved, PPTX via python-pptx
including speaker notes, VTT/SRT into time windows. See
[extraction.md](internals/extraction.md).

**Gate**
```bash
uv run studykb review --corpus <name> --what summary --what extraction
```
`SUMMARY.md` must show **every source is indexed** and **no page with text was
dropped**. In the table, `pages` reads with-text/total: `0/137` means a document
extracted to nothing. Then open `extraction.md` for any source SUMMARY flagged.

### 2.3 Document intelligence — OCR 🟡

Scanned PDFs get a text layer. The trigger is measured, not guessed: mean
characters per page after boilerplate is subtracted, against
`extract.ocr.trigger_chars_per_page`. OCR writes a **copy**; originals are never
modified.

**Why 🟡**: no source in the corpus has ever needed it, so the path has never
run end to end. `ocrmypdf` is also absent from the host, so it can only run in
the container.

**Gate — to build**: `studykb selftest ocr`, which renders a synthetic
image-only PDF, runs it through the real trigger and the real command, and
asserts the text comes back. Until that exists, the manual gate is: put a
scanned PDF in the test corpus, run ingest **in the container**, and confirm
SUMMARY shows chunks for it with `provenance: ocr`.

### 2.4 Lecture transcripts ⬜

The captions themselves. The extractor is written and tested against a fixture;
what is missing is the material — the `.vtt` files have never been downloaded
from the university platform.

**Gate**: drop one real `.vtt` into `test-corpus/transcripts/`, ingest, then
`review --what chunks` and confirm the locators read `@HH:MM:SS` and that
opening one of those timestamps in the recording lands on the topic (±1 min).

---

## Phase 3 — Making it searchable

### 3.1 Vision captioning ✅

Figure-heavy slide pages are rendered and described so they can be found. Off
for prose — measured, see [enrichment.md](internals/enrichment.md).

**Gate**
```bash
uv run studykb review --corpus <name> --what captions
```
`captions.md` puts each page image directly above the model's claim about it.
Read down. Anything describing something not in the picture is a defect, and the
report also names every source with no captions and why.

### 3.2 ASR cleanup 🟡

Auto-captions are repaired against a glossary built from the timetable. Written
and wired; never run, because there are no transcripts.

**Gate**: after 2.4, compare a corrected window against the raw one — both are
kept, the raw text is in `extra.raw`. The correction must fix terminology
without shortening or paraphrasing.

### 3.3 Chunking ✅

Units become chunks. See [chunking.md](internals/chunking.md).

**Gate**
```bash
uv run studykb review --corpus <name> --what chunks
```
`chunks.md` shows each chunk's opening and closing words. Scan the pairs for
cuts landing mid-derivation. The header states the median size and how many
chunks fell below the ceiling.

### 3.4 Indexing ✅

Embeddings into Qdrant under deterministic ids, with a payload index on
`module`, `type`, `provenance`, `source` and full text.

**Gate**: the SUMMARY check **nothing was lost on the way in** — chunks produced
against chunks in the collection. A mismatch means ids collided and chunks
overwrote each other, which is exactly how the caption-over-page bug looked from
outside.

### 3.5 Retrieval ✅

Dense search plus a term-filtered branch, fused with RRF. See
[indexing-retrieval.md](internals/indexing-retrieval.md).

**Gate**
```bash
uv run studykb review --corpus <name> --what retrieval
```
Edit `corpora/<name>/queries.yaml` to ask what you would actually ask. Then
**open the locators** — a citation that does not survive being checked makes
every note built on it worthless.

---

## Phase 4 — Using it

### 4.1 Syllabus from the timetable 🟡

The course publishes no syllabus; the timetable spreadsheet is parsed into
modules, dates, teachers and lecture topics, which feed module assignment, the
vault pages and the ASR glossary. See [calendar.md](internals/calendar.md).

**Why 🟡**: parsing is covered by tests against the real file, but the generated
`vault/00-syllabus/M*.md` pages have never been checked against the spreadsheet
by eye.

**Gate — to build**: include the syllabus in `review`, so lectures per module,
date ranges and assessment dates can be compared against the source in one
place.

### 4.2 MCP and HTTP serving 🟡

`kb_search`, `kb_outline`, `kb_lecture`, `kb_sources` over MCP, plus
`GET /search` and `/healthz`.

**Why 🟡**: it runs and Claude Code connects, but nothing validates the tools
themselves — a tool could return wrong results and only a human would notice.

**Gate — to build**: `studykb selftest serve`, calling each tool once and
checking the shape of what comes back. Manual gate today:
```bash
curl -s localhost:8077/healthz
claude mcp list          # must show studykb ✔ Connected
```

### 4.3 Multi-corpus isolation ✅

Each corpus owns its collection, its state file and its vault.

**Gate**
```bash
uv run studykb ingest --corpus A --dry-run   # before
uv run studykb ingest --corpus B             # run the other one
uv run studykb ingest --corpus A --dry-run   # must be unchanged
```
If corpus A now has work pending, or reports sources "missing from disk", the
isolation is broken.

---

## Phase 5 — Operations

This is the phase that decides whether the application survives contact with
months of use. Almost none of it exists.

### 5.1 Backup and restore ⬜

What must survive a disk failure, in order of irreplaceability:

1. **the vault** — your notes. Cannot be regenerated by anything.
2. **the corpus** — re-downloadable, slowly.
3. `state.db` — rebuildable, at the cost of a full reprocess.
4. Qdrant — fully derived, rebuild in minutes.

Nothing backs any of this up today, and the vault is the one that matters.

**Gate — to build**: `studykb backup` producing a dated archive, and a restore
drill that rebuilds into an empty directory and ends with `review` green.

### 5.2 Scheduled incremental update ⬜

New material arrives weekly. Ingestion is incremental by construction but must
be run by hand every time.

**Gate — to build**: a scheduled run that ingests, runs `review --what summary`,
and reports only when a check is not green.

### 5.3 Continuous integration ⬜

19 tests exist and run only when someone remembers.

**Gate — to build**: a GitHub Actions workflow running `uv run pytest` on push.
Gate is a green badge and a failing PR when a test breaks.

### 5.4 Run history ⬜

Every ingest prints a table and forgets it. There is no way to answer "when did
this source last change, and what did that run do".

`state.db` already stores `done_at` per (source, stage), so the data is half
there.

**Gate — to build**: `studykb history`, listing recent runs with what each one
processed.

### 5.5 Rebuild from scratch 🟡

The reconciliation guard already catches the dangerous half: an empty collection
that the state claims is indexed triggers a reindex rather than leaving search
permanently empty.

**Why 🟡**: never exercised deliberately, and there is no single command to
rebuild everything.

**Gate — to build**: `studykb rebuild --corpus <name>`, which drops derived
state and reruns, ending with `review` green against the same numbers as before.

### 5.6 Versioning and release ⬜

`version = "0.1.0"` in `pyproject.toml`, unused. The image is `:latest`, so
there is no way to say which build produced an index.

**Gate — to build**: a version stamped into the image and reported by `doctor`,
and recorded in the state database alongside each run.

---

## Where it stands

| phase | ✅ | 🟡 | ⬜ |
|---|---|---|---|
| 1 Runtime | 2 | 0 | 0 |
| 2 Material in | 2 | 1 | 1 |
| 3 Searchable | 4 | 1 | 0 |
| 4 Using it | 1 | 2 | 0 |
| 5 Operations | 0 | 1 | 5 |

**The platform works and is verifiable. The operations around it do not exist.**

Two things block the 🟡s rather than any amount of coding: a scanned PDF for
2.3, and lecture captions for 2.4 and 3.2. Both are material to obtain, not
software to write.

The highest-value ⬜ is **5.1 backup**, because the vault is the only thing in
the system that cannot be regenerated.

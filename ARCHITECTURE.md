# Architecture

High-level: what the application is and how data moves through it. For the
terms used here, read [docs/glossary.md](docs/glossary.md) first; for how a
subsystem actually works, follow the links in
[docs/README.md](docs/README.md). For what is built and what is missing, see
[docs/DELIVERY.md](docs/DELIVERY.md).

## Two forces shaped everything

**The corpus grows.** Material arrives in waves, so a full reprocess is never
acceptable. Every `(source, stage)` pair records the source checksum and a
fingerprint of exactly the config that stage consumes. Adding forty PDFs costs
those forty; editing `caption_slide.j2` reruns vision and leaves the embeddings
alone; rerunning unchanged does no work at all.

**8 GB of VRAM.** The embedder, the vision model and the text model cannot be
resident together. So ingest is staged across *all* sources rather than looping
sources across all stages: each model loads once per run instead of once per
file, and the previous one is evicted before the next stage starts.

## Flow

```
corpus.yaml globs
      │
      ▼
  discover ──► module assignment (path regex → calendar date → MANIFEST.md)
      │
      ├─ ocr          no GPU     PDFs with no text layer → searchable copy in /data
      ├─ extract      no GPU     pymupdf4llm / python-pptx / webvtt-py → Units
      ├─ asr_cleanup  text model transcript windows repaired with a glossary
      ├─ vision       VLM        figure-heavy pages rendered and captioned
      └─ embed        embedder   Units → Chunks → Qdrant
```

`Unit` is one page, one slide or one five-minute transcript window. `Chunk` is
what gets embedded. Both carry `locator` and `provenance` — see the README for
why that is the load-bearing part.

Per stage: [discovery](docs/internals/discovery.md) ·
[extraction and OCR](docs/internals/extraction.md) ·
[vision and ASR](docs/internals/enrichment.md) ·
[chunking](docs/internals/chunking.md) ·
[indexing and retrieval](docs/internals/indexing-retrieval.md) ·
[what makes a stage rerun](docs/internals/state.md)

## Decisions

**Qdrant over pgvector.** Payload filtering (`module`, `type`, `provenance`) and
the full-text index are native, so there is no SQL and no migration when a
payload field is added.

**Deterministic chunk ids.** `uuid5(namespace, source|locator|index)`. A
re-index overwrites rather than duplicating. The namespace is a constant on
purpose: changing it orphans every indexed point.

**Hybrid search is two dense branches, not BM25.** One unfiltered, one
restricted to chunks whose full-text index contains the query terms, fused
server-side with RRF. That rescues exact tokens — `QUBO`, `Grover`, a lecturer's
name — which a dense embedder smooths away. It costs one prefetch and no
dependency. Real BM25 or a cross-encoder goes in if a concrete query is found to
fail.

**Vision is off for prose, and that was a measured result, not a guess.**
The first run captioned books as well as slides. Two things went wrong. The
`auto` trigger fires on low-text pages, and in a book those are the covers,
title pages and blanks — the real figures live on pages surrounded by text and
were never sent. And on a cover, qwen2.5-vl:7b does not answer "this is a
cover": it pattern-completes from the title. Page 1 of Nielsen & Chuang came
back as "a circuit diagram with qubits labelled A, B, C, a Hadamard gate and a
table below" — the page is the front cover. Fabricated text entering the index
under a provenance tag most readers will skim past is worse than no text, so
books and papers are now `vision: never`, a graphics floor keeps covers and
blanks away from the model even on slides, and the prompt names the cover case
explicitly. Slides remain worth captioning: there the content genuinely is the
figure.

**OCR writes a copy.** The corpus is mounted read-only. Some of this material
exists in one copy only, and a pipeline that rewrites originals in place is one
bad ocrmypdf run from losing a book.

**The timetable is the syllabus.** The course publishes no syllabus document;
the timetable spreadsheet is the only record of what each lecture covered.
`calendar.py` parses it into modules, dates, teachers and topics, which then feed
module assignment, the vault syllabus pages, and the ASR glossary. The sheet is
built for humans — blank continuation rows, inconsistent module spellings, two
hand-typed year slips — and all of that is absorbed there so it stays out of the
rest of the codebase.

**One OpenAI-compatible client.** ollama, LM Studio, vLLM and the hosted APIs
all speak it. There is no provider abstraction layer because there is nothing
for it to abstract.

## Adding a subject

1. `corpora/<domain>/corpus.yaml` — globs, module rules, glossary, optional
   calendar.
2. `corpora/<domain>/MANIFEST.md` — the overrides for what the rules cannot
   place.
3. `studykb ingest --corpus <domain>`.

No step touches `src/`. If it does, the design has leaked and the fix is to move
the fact into the manifest.

# studykb documentation

Start here.

## To understand the system

| document | answers |
|---|---|
| [../ARCHITECTURE.md](../ARCHITECTURE.md) | what the application is, how data flows through it, why it is shaped this way |
| [glossary.md](glossary.md) | the eight terms that appear everywhere — **read this first** |
| [internals/](internals/) | one document per subsystem, following the data with function and file names |

## To use it

| document | answers |
|---|---|
| [HOWTO.md](HOWTO.md) | **step by step: start, ingest, check, search.** Start here to operate the system |

## To build and verify it

| document | answers |
|---|---|
| [STATE.md](STATE.md) | **where this is right now** — pending work, what is blocked, decisions taken. Read first when resuming |
| [DELIVERY.md](DELIVERY.md) | every macro-capability the finished application needs, what exists, what is missing, and the command that validates each one |

## To operate it

| document | answers |
|---|---|
| [../README.md](../README.md) | setup, commands, what is deliberately not built |
| [agents/](agents/) | playbooks for the models that run the pipeline and write notes |

## Subsystems

Read in this order — each one consumes the output of the one above.

| # | subsystem | source | document |
|---|---|---|---|
| 1 | Configuration | `config.py` | [configuration.md](internals/configuration.md) |
| 2 | Discovery | `pipeline.py` | [discovery.md](internals/discovery.md) |
| 3 | Extraction (document intelligence) | `extract/` | [extraction.md](internals/extraction.md) |
| 4 | Enrichment (vision, ASR) | `extract/vision.py`, `extract/asr.py` | [enrichment.md](internals/enrichment.md) |
| 5 | Chunking | `chunk.py` | [chunking.md](internals/chunking.md) |
| 6 | Indexing and retrieval | `index.py`, `search.py` | [indexing-retrieval.md](internals/indexing-retrieval.md) |
| 7 | Incremental state | `state.py` | [state.md](internals/state.md) |
| 8 | Syllabus | `calendar.py` | [calendar.md](internals/calendar.md) |
| 9 | Serving | `server.py` | [serving.md](internals/serving.md) |
| 10 | Review | `review.py` | [review.md](internals/review.md) |
| 11 | Metrics | `metrics.py` | [metrics.md](internals/metrics.md) |

## A note on what these documents are for

The code carries its own comments, and they explain *why* a line is the way it
is. These documents explain *what happens in what order* and *where to look*,
which a comment cannot: no comment can tell you that a caption is produced four
stages after the page it describes, or that the thing making a stage rerun is a
fingerprint computed somewhere else entirely.

Where a document and the code disagree, the code is right and the document is a
bug.

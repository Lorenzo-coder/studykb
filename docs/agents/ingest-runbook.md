# Runbook: operating an ingest

For mechanical execution. Follow the steps; do not improvise, and do not open
corpus files to "check" anything.

## Normal run

```bash
uv run studykb doctor                                  # must exit 0
uv run studykb ingest --corpus qml-master --dry-run    # shows what would run
uv run studykb ingest --corpus qml-master
```

Report back: the per-stage table, the chunk count, and any unassigned sources.
Nothing else.

## Stage order and what each needs

| stage | needs | notes |
|---|---|---|
| `ocr` | tesseract, no GPU | only PDFs with almost no text layer |
| `extract` | nothing | always runs for a new or changed file |
| `asr_cleanup` | text model in VRAM | transcripts only |
| `vision` | vision model in VRAM | slide-type PDFs and figure-heavy pages |
| `embed` | embedding model in VRAM | always last |

Stages share one 8 GB GPU and run one at a time. A run that seems stuck on
`vision` is usually just slow: a page takes seconds, a deck takes minutes.

## Errors

| symptom | action |
|---|---|
| `doctor`: `✗ vlm: qwen2.5vl:7b` | `ollama pull qwen2.5vl:7b`, rerun `doctor` |
| `doctor`: `✗ Qdrant unreachable` | `docker compose up -d qdrant`, wait for healthy |
| `doctor`: `! ocrmypdf missing` | expected outside the container; run ingest via `docker compose run --rm studykb` |
| `error ocr <file>` | report the filename, continue. One bad PDF does not stop a run |
| `error vision <file>` | same. The fallback model already tried |
| `collection ... has dim N but config says M` | stop. Changing the embedding model means a reindex — ask first |
| ingest reports `N sources with no module` | see `tagging.md` |
| `N known sources are missing from disk` | do **not** run `forget`. Check the corpus volume is mounted first, then ask |

## Reruns

Rerunning is free for unchanged files. To force one stage after editing a
prompt or a threshold, just rerun: the fingerprint changed and only that stage
re-executes.

```bash
uv run studykb ingest --corpus qml-master --only vision
```

Never delete `state.db` to "start clean" — that discards hours of GPU work.

# Configuration

`src/studykb/config.py` · 245 lines

Two layers, both data, never code. The split is the whole point: one says *how*
to index, the other says *what*.

| layer | file | scope |
|---|---|---|
| how | `config/default.yaml` | models, thresholds, storage, chunking, retrieval |
| what | `corpora/<domain>/corpus.yaml` | globs, types, module rules, timetable, glossary |

## Loading

`load_config(path)` reads `config/default.yaml`, then deep-merges two overrides
in order:

1. `config/local.yaml` — gitignored, and excluded from the Docker image by
   `.dockerignore`. This is for host-side development: it points Qdrant and
   ollama at `localhost` instead of the container hostnames. It once leaked into
   the image and silently overrode the container's own paths.
2. environment variables. `STUDYKB__MODELS__LLM__NAME=foo` becomes
   `{"models": {"llm": {"name": "foo"}}}` — the prefix is stripped, `__` splits
   levels, and the value is parsed as YAML so `true` and `8192` arrive typed.
   This is how `docker-compose.yml` points the container at `qdrant:6333`.

`load_corpus(domain)` reads `corpora/<domain>/corpus.yaml` and records where it
came from in `manifest_dir`, so `MANIFEST.md` and `queries.yaml` are found beside
it.

Both return pydantic models, so **a typo in YAML fails at `doctor` time** rather
than four hours into an ingest.

## Corpus-level overrides

Three fields in `corpus.yaml` let a corpus own its resources instead of sharing
the global ones:

| field | overrides | why it exists |
|---|---|---|
| `collection` | `storage.collection` | a test corpus must not write into the real index |
| `vault` | `storage.vault` | a review run must not leave files among your course notes |
| *(derived)* | `storage.state_db` | see below |

They are applied in one place, `cli.py::_load`, so every command gets them.
`_load` also derives the state file name — `state-<domain>.db` — rather than
reading it from the manifest, because sharing that file is not a choice anyone
should be able to make. Two corpora on one state file make each other's sources
read as "missing from disk" and let one corpus's empty collection wipe the
other's embed records.

`--root` is the fourth override, on the command line only: the manifest says
`/corpus`, which exists in the container and nowhere else.

## Fingerprints

`Config.fingerprint(prompt_version)` returns one hash per stage over exactly what
that stage consumes. This is what makes ingestion incremental — see
[state.md](state.md) for how it is used.

Three details that are easy to get wrong:

- **The prompt fingerprint is folded only into the two stages that send a
  prompt** (`vision`, `asr_cleanup`). Folding it into `embed` would rebuild the
  whole index every time a caption prompt is reworded.
- **The chunk config is folded into `embed`**, because changing chunk size
  changes what gets embedded.
- **Config changes invalidate a stage; code changes do not.** There are literal
  version constants — `"ocr": {... "code": "v2"}`, `"extract": "v3"` — to bump
  by hand when the extraction logic changes. Forget, and the next run keeps last
  week's wrong output and reports success.

## Adding a setting

1. Add the field to the right pydantic model in `config.py`, with a default.
2. Add it to `config/default.yaml` with a comment saying what it trades off.
3. If a stage's behaviour depends on it, make sure that stage's fingerprint
   covers it — otherwise changing it will not cause a rerun.

Step 3 is the one that gets skipped.

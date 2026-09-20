# Incremental state

`src/studykb/state.py` · 137 lines · and `pipeline.py::_effective_fp`

The corpus grows every week. A full reprocess is never acceptable, so every
stage is gated.

## The two tables

```sql
stage_state (source, stage, source_sha, cfg_fp, output_ref, done_at)
seen_sources (source, source_sha, type, module, last_seen)
```

`stage_state` answers "must this stage run for this source". `seen_sources` is
the inventory, used to notice files that have disappeared.

## The gate

```python
def needs(source, stage, source_sha, cfg_fp) -> bool:
    row = ...
    return row is None or row[0] != source_sha or row[1] != cfg_fp
```

A stage reruns when the file changed or when the fingerprint changed. Nothing
else. Rerunning with nothing changed does no work at all.

## Upstream dependencies

A stage consumes the output of the stages above it, so its gate has to move when
theirs does:

```python
_UPSTREAM = {
    "extract":     ("ocr",),
    "asr_cleanup": ("extract",),
    "vision":      ("extract",),
    "embed":       ("extract", "asr_cleanup", "vision"),
}
```

`_effective_fp` joins a stage's own fingerprint with those of its upstream
stages — **but only the ones that apply to that source**. So editing the caption
prompt reindexes the slides and leaves the books alone: a book is never
captioned, and must not pay for a rebuild it cannot benefit from.

Without this, new captions sat in a file the embed stage never read again while
every run reported success.

## Reconciliation

```python
if index.total(client, cfg) == 0:
    cleared = st.clear_stage("embed")
```

If the collection is empty but the state says everything is indexed, the state is
lying — a dropped collection, a lost volume, a Qdrant upgrade that could not read
its own storage. Believing it would leave search permanently empty with every run
reporting success.

Only the `embed` rows are cleared. Extraction and captions behind them are still
valid and cost hours.

## One state file per corpus

`cli.py::_load` derives `state-<domain>.db`. This is not configurable, because
sharing it is not a choice anyone should be able to make.

When it was shared, ingesting the test corpus did two things to the real one:
every source of the real corpus read as "missing from disk", and the test
corpus's empty collection convinced the reconciliation guard that the real
corpus's embed state was lying — wiping all fifteen rows.

## Deletions are reported, never acted on

```python
def vanished(self, present: set[str]) -> list[str]:
    return sorted(known - present)
```

An unmounted volume looks exactly like a mass deletion. Dropping the chunks is
the operator's call, via `studykb forget <path>`.

## What the fingerprint does not cover

**Code changes.** Only config is hashed. There are manual version constants in
`config.py::fingerprint` — `"extract": "v4"`, `"ocr": {... "code": "v2"}` — to
bump when extraction or OCR logic changes. Forget, and the next run keeps last
week's wrong output and calls it done.

## Gate

```bash
uv run studykb ingest --corpus <name> --dry-run   # run twice
```

The second run must report zero work. Then touch one file and confirm only that
file is processed.

Isolation between corpora:

```bash
uv run studykb ingest --corpus A --dry-run   # note the numbers
uv run studykb ingest --corpus B
uv run studykb ingest --corpus A --dry-run   # must be identical
```

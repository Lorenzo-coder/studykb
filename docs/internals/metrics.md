# Metrics

`src/studykb/metrics.py` · `cli.py::stats`

A full ingest is tens of minutes of GPU time. The only way to know whether a
change made it cheaper — a different embedder, a higher graphics floor, a
shorter caption prompt — is to have measured the run before it. So every stage
writes one row and the rows survive.

## Where they live

In `state.db`, the same SQLite file that drives incremental ingestion. No new
dependency, no service to run, and the history sits beside the state it
describes: delete one and you delete the other, which is correct, because a
cost history for an index that no longer exists is noise.

```sql
CREATE TABLE runs (
    run_id, stage, corpus,
    started, seconds,
    sources, items,                          -- items = pages, captions or chunks
    llm_calls, llm_seconds, tokens_in, tokens_out,
    gpu_wh, gpu_peak_w,                      -- null where nvidia-smi is absent
    errors,
    PRIMARY KEY (run_id, stage)
);
```

One row per (run, stage). A run that only does `--only vision` writes one row,
and it is still comparable with the same stage in a full run.

## What is measured, and where from

**Wall time** comes from `perf_counter` around each stage. It is the number
that decides whether to start a run before lunch or before bed.

**Model calls and tokens** come from `LLM._post`, which is the single point
every model call passes through — embeddings, captions and ASR cleanup alike.
Counting there means no stage had to be touched to be measured, and a stage
added later is measured without anyone remembering to. Tokens are read from the
`usage` block that every OpenAI-compatible endpoint returns; ollama fills it in.

A call is counted **even when it raises**. A failed call still burned the time
it burned, and a stage that fails slowly is exactly the thing worth seeing.

**Energy** is integrated from `nvidia-smi --query-gpu=power.draw`, sampled every
two seconds on a daemon thread while the stage runs. A sample costs ~25 ms, so
the meter is about 1% of one core.

Sampling rather than reading at both ends is the point: a stage that loads a
model, works for eight minutes and then idles is not described by either
endpoint. Where `nvidia-smi` is missing, the thread never starts, the two
columns stay null, and everything else works unchanged.

## What the energy figure is not

It is **whole-GPU draw**, not this process's share. During an ingest nothing
else should be using the card, but if something is, the number is an upper
bound. `nvidia-smi` reports no per-process power, so the alternative was to
report nothing.

It also excludes the CPU, the disk and the rest of the machine. Extraction and
chunking are CPU work and show as wall time with no watt-hours, which is
accurate about the GPU and silent about everything else.

## Reading it back

```bash
uv run studykb stats --corpus qml-master              # last 10 runs
uv run studykb stats --corpus qml-master -n 40        # more
uv run studykb stats --corpus qml-master --run a1b2c3 # one run, by stage
```

`ingest` also prints the table for the run it just finished, so the common case
needs no second command.

Metrics that are written and never read are waste, which is why `stats` exists
in the same change as the table.

## What to look at

| question | column |
|---|---|
| should I start this now or tonight? | `time`, total row |
| which stage is the expensive one? | `time` per stage |
| did a config change help? | compare `per item` across runs, not `time` — the corpus grows |
| is a source pathological? | `per item` on a stage that normally runs flat |
| what did the run draw? | `Wh`, and `peak W` against the card's limit |

`per item` is the one to compare between runs. Total time rises simply because
the corpus grew; time per page or per chunk does not.

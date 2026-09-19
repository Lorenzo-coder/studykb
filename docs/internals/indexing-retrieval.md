# Indexing and retrieval

`src/studykb/index.py` · 90 lines · `src/studykb/search.py` · 125 lines

## Qdrant, not pgvector

Payload filtering (`module`, `type`, `provenance`, `source`) and a full-text
index are native, so there is no SQL to write and no migration when a payload
field is added.

`ensure_collection` refuses to proceed when the collection's vector size differs
from `models.embed.dim`:

```
collection 'studykb' has dim 1024 but config says 768.
Changing the embedding model means reindexing.
```

A silent mismatch would poison every search result without any error.

> **Operational note.** Qdrant does not support jumping many minor versions in
> place. Upgrading v1.12 → v1.19 over an existing volume makes the server
> refuse to start: `unknown variant 'on_disk'`. The volume is derived data and
> can be recreated, but expect a reindex.

## Upserts

`upsert` writes points under the deterministic `chunk_id`. `_stage_embed` calls
`drop_source` **first**:

```python
index.drop_source(client, cfg, src.rel)
index.upsert(client, cfg, chunks, vectors)
```

Without the drop, a shorter re-extraction leaves the tail of the previous run's
chunks orphaned in the collection, still searchable and no longer matching the
document.

## Retrieval

`search()` issues two prefetch branches and lets Qdrant fuse them with RRF:

| branch | what it does |
|---|---|
| dense | plain nearest-neighbour over the whole collection |
| dense + text filter | the same query vector, restricted to chunks whose full-text index contains the query terms |

The second branch rescues exact tokens — `QUBO`, `Grover`, a lecturer's surname
— which a dense embedder smooths away.

**It is not BM25, and the code says so.** Ranking inside both branches is by
vector distance; the lexical part is a hard filter, not a score. It costs one
extra prefetch and no dependency. A real cross-encoder reranker goes in if a
concrete query is found to fail — there is a commented compose profile for
`bge-reranker-v2-m3` waiting.

Terms shorter than three characters are dropped from the filter: they match
everything and make the branch meaningless.

## Formatting for an agent

`format_hits` leads every block with its citation **and its provenance**:

```
[1] Schuld — Machine Learning with Quantum Computers p.149 — 4.3 Variational circuits
    module=M7 type=book provenance=text-layer score=1.000
```

Without the provenance line, a caption written by a 7B vision model and a
passage read from the book look identical in an agent's context.

## Gate

Indexing is covered by the SUMMARY check **nothing was lost on the way in** —
chunks produced against chunks in the collection. A mismatch means ids collided.

Retrieval:

```bash
uv run studykb review --corpus <name> --what retrieval
```

Queries come from `corpora/<name>/queries.yaml`. The `expect` field is a prompt
to look, not a pass/fail — retrieval that finds a better source than you guessed
is not a failure. **Open the locators.**

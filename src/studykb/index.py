"""Qdrant collection management and upserts.

Chosen over pgvector because payload filtering (`module`, `type`,
`provenance`) and the full-text index come for free, so there is no SQL to
write and no schema to migrate when a payload field is added.

Point ids are the deterministic ``chunk_id``, so re-indexing a source overwrites
its previous chunks instead of duplicating them.
"""

from __future__ import annotations

from collections.abc import Iterable

from qdrant_client import QdrantClient, models

from .config import Config
from .types import Chunk

# Payload fields that get an index. Keyword fields drive filtering; `text` gets a
# full-text index so the lexical branch of hybrid search can use it.
KEYWORD_FIELDS = ("module", "type", "provenance", "source", "authority")


def connect(cfg: Config) -> QdrantClient:
    return QdrantClient(url=cfg.storage.qdrant_url, timeout=120)


def ensure_collection(client: QdrantClient, cfg: Config) -> None:
    name = cfg.storage.collection
    dim = cfg.models.embed.dim

    if client.collection_exists(name):
        existing = client.get_collection(name).config.params.vectors.size  # type: ignore[union-attr]
        if existing != dim:
            raise RuntimeError(
                f"collection '{name}' has dim {existing} but config says {dim}. "
                f"Changing the embedding model means reindexing: drop the collection "
                f"and clear the embed rows in state.db."
            )
        # A field added after the collection was created still needs its index.
        known = client.get_collection(name).payload_schema
        for field in KEYWORD_FIELDS:
            if field not in known:
                client.create_payload_index(name, field, models.PayloadSchemaType.KEYWORD)
        return

    client.create_collection(
        collection_name=name,
        vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
    )
    for field in KEYWORD_FIELDS:
        client.create_payload_index(name, field, models.PayloadSchemaType.KEYWORD)
    client.create_payload_index(name, "text", models.PayloadSchemaType.TEXT)


def upsert(client: QdrantClient, cfg: Config, chunks: list[Chunk], vectors: list[list[float]]) -> None:
    if not chunks:
        return
    if len(chunks) != len(vectors):
        raise ValueError(f"{len(chunks)} chunks but {len(vectors)} vectors")
    client.upsert(
        collection_name=cfg.storage.collection,
        points=[
            models.PointStruct(id=c.id, vector=v, payload=c.payload())
            for c, v in zip(chunks, vectors, strict=True)
        ],
    )


def drop_source(client: QdrantClient, cfg: Config, source: str) -> None:
    """Remove every chunk of one source, for re-ingest and for deletions."""
    client.delete(
        collection_name=cfg.storage.collection,
        points_selector=models.FilterSelector(
            filter=models.Filter(must=[models.FieldCondition(key="source", match=models.MatchValue(value=source))])
        ),
    )


def counts_by(client: QdrantClient, cfg: Config, field: str, values: Iterable[str]) -> dict[str, int]:
    return {
        value: client.count(
            cfg.storage.collection,
            count_filter=models.Filter(
                must=[models.FieldCondition(key=field, match=models.MatchValue(value=value))]
            ),
            exact=True,
        ).count
        for value in values
    }


def total(client: QdrantClient, cfg: Config) -> int:
    return client.count(cfg.storage.collection, exact=True).count

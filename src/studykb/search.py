"""Retrieval.

Hybrid search here means two prefetch branches fused server-side with RRF:

1. plain dense nearest-neighbour over the whole collection;
2. the same dense query restricted to chunks whose full-text index actually
   contains the query terms.

That second branch is what rescues exact tokens — ``QUBO``, ``Grover``,
``Corazza`` — which a dense embedder happily smooths away. It is not BM25:
ranking inside the branch is still by vector distance, and the lexical part is a
hard filter. It costs one extra prefetch and no extra dependency; a real
reranker goes in only if a concrete query is found to fail.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from qdrant_client import QdrantClient, models

from .config import Config
from .limits import SEARCH_PASSAGE
from .llm import LLM

# Short tokens are noise as filter terms; they match everything.
_TERM = re.compile(r"[A-Za-z0-9_\-]{3,}")


@dataclass
class Hit:
    score: float
    text: str
    source_title: str
    locator: str
    module: str | None
    type: str
    provenance: str
    heading: str

    def cite(self) -> str:
        return f"{self.source_title} {self.locator}"


def _filter(module: str | None, type_: str | None, terms: list[str] | None) -> models.Filter | None:
    must: list[models.Condition] = []
    if module:
        must.append(models.FieldCondition(key="module", match=models.MatchValue(value=module)))
    if type_:
        must.append(models.FieldCondition(key="type", match=models.MatchValue(value=type_)))
    should = [models.FieldCondition(key="text", match=models.MatchText(text=t)) for t in (terms or [])]
    if not must and not should:
        return None
    return models.Filter(must=must or None, should=should or None)


def search(
    client: QdrantClient,
    cfg: Config,
    llm: LLM,
    query: str,
    *,
    module: str | None = None,
    type_: str | None = None,
    k: int | None = None,
) -> list[Hit]:
    k = k or cfg.retrieval.k_final
    vector = llm.embed([query])[0]
    r = cfg.retrieval

    if r.hybrid and (terms := _TERM.findall(query)):
        result = client.query_points(
            collection_name=cfg.storage.collection,
            prefetch=[
                models.Prefetch(query=vector, filter=_filter(module, type_, None), limit=r.k_dense),
                models.Prefetch(query=vector, filter=_filter(module, type_, terms), limit=r.k_lexical),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=k,
            with_payload=True,
        )
    else:
        result = client.query_points(
            collection_name=cfg.storage.collection,
            query=vector,
            query_filter=_filter(module, type_, None),
            limit=k,
            with_payload=True,
        )

    return [_hit(p) for p in result.points]


def _hit(point: models.ScoredPoint) -> Hit:
    p = point.payload or {}
    return Hit(
        score=point.score,
        text=p.get("text", ""),
        source_title=p.get("source_title", p.get("source", "?")),
        locator=p.get("locator", ""),
        module=p.get("module"),
        type=p.get("type", "?"),
        provenance=p.get("provenance", "?"),
        heading=p.get("heading", ""),
    )


def format_hits(hits: list[Hit], max_chars: int = SEARCH_PASSAGE) -> str:
    """Render hits for an agent.

    Every block leads with its citation and its provenance, so a caption written
    by a 7B vision model is never mistaken for the source text.
    """
    if not hits:
        return "No results."
    blocks = []
    for i, h in enumerate(hits, 1):
        text = h.text if len(h.text) <= max_chars else h.text[:max_chars] + " […]"
        head = f" — {h.heading}" if h.heading else ""
        blocks.append(
            f"[{i}] {h.cite()}{head}\n"
            f"    module={h.module or '-'} type={h.type} provenance={h.provenance} score={h.score:.3f}\n"
            f"{text}"
        )
    return "\n\n".join(blocks)

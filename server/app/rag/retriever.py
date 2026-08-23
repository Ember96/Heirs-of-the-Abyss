"""Hybrid retrieval: dense (Cohere) + BM25 + payload filters + RRF fusion.

`search_local` is the deterministic, dependency-free fallback used for tests
and whenever embeddings are unavailable (no key, API down). When a Cohere key
is configured, `hybrid_search` embeds the query + records, ranks both ways,
and fuses with RRF — no Qdrant/docker required for the local single-process path.
"""

from __future__ import annotations

import math

import httpx

from .. import config
from .indexer import render_record


def tokenize(text: str) -> list[str]:
    return text.lower().split()


def rrf_fusion(ranked_lists: list[list[str]], k: int = 60) -> list[str]:
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return [doc_id for doc_id, _ in sorted(scores.items(), key=lambda x: -x[1])]


def _matches_filters(record: dict, filters: dict) -> bool:
    return all(record.get(key) == value for key, value in filters.items())


def search_local(query: str, records: list[dict], limit: int = 5, filters: dict | None = None) -> list[dict]:
    q_terms = set(tokenize(query))
    scored: list[tuple[int, dict]] = []
    for record in records:
        if filters and not _matches_filters(record, filters):
            continue
        score = len(q_terms & set(tokenize(render_record(record))))
        if record.get("name", "").lower() in query.lower():
            score += 10
        scored.append((score, record))
    scored.sort(key=lambda x: -x[0])
    return [record for _, record in scored[:limit]]


def embed_texts(texts: list[str], *, input_type: str) -> list[list[float]] | None:
    """Cohere embeddings; returns None when unavailable so callers fall back to BM25."""
    if not config.COHERE_API_KEY or not texts:
        return None
    try:
        resp = httpx.post(
            "https://api.cohere.com/v2/embed",
            headers={"Authorization": f"Bearer {config.COHERE_API_KEY}"},
            json={
                "model": config.COHERE_EMBED_MODEL,
                "texts": texts,
                "input_type": input_type,
                "embedding_types": ["float"],
            },
            timeout=30.0,
        )
        if resp.status_code != 200:
            return None
        payload = resp.json()["embeddings"]
        return payload["float"] if isinstance(payload, dict) else payload
    except httpx.HTTPError:
        return None


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


_DOC_CACHE: dict[int, list[list[float]]] = {}


def _document_embeddings(records: list[dict]) -> list[list[float]] | None:
    fingerprint = hash(tuple((r.get("id", ""), r.get("name", "")) for r in records))
    cached = _DOC_CACHE.get(fingerprint)
    if cached is not None:
        return cached
    vectors = embed_texts([render_record(r) for r in records], input_type="search_document")
    if vectors is not None:
        _DOC_CACHE.clear()
        _DOC_CACHE[fingerprint] = vectors
    return vectors


def hybrid_search(query: str, records: list[dict], limit: int = 5, filters: dict | None = None) -> list[dict]:
    """Dense + BM25 fused with RRF. Falls back to pure BM25 without embeddings."""
    filtered = [r for r in records if not filters or _matches_filters(r, filters)]
    bm25 = search_local(query, filtered, limit=max(limit * 2, 10))

    q_vec = embed_texts([query], input_type="search_query")
    doc_vecs = _document_embeddings(filtered)
    dense: list[str] = []
    if q_vec and doc_vecs:
        scored = sorted(
            (( _cosine(q_vec[0], dv), rid) for rid, dv in zip([r.get("id", "") for r in filtered], doc_vecs)),
            key=lambda x: -x[0],
        )
        dense = [rid for _, rid in scored[: max(limit * 2, 10)]]

    if not dense:
        return bm25[:limit]
    by_id = {r.get("id", ""): r for r in filtered}
    fused = rrf_fusion([dense, [r.get("id", "") for r in bm25]])
    return [by_id[rid] for rid in fused if rid in by_id][:limit]


class Retriever:
    """Local hybrid retrieval over an in-memory record set.

    Qdrant/docker is a documented scale-out path (vector persistence across
    restarts, multi-process sharing), not shipped code — see docs/08.
    """

    def retrieve(self, query: str, records: list[dict], limit: int = 5, filters: dict | None = None) -> list[dict]:
        return hybrid_search(query, records, limit, filters)

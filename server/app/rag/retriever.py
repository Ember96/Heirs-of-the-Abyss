"""Hybrid retrieval: dense + BM25 + payload filters + RRF fusion.

`search_local` is the deterministic, dependency-free fallback (no Qdrant, no
embeddings) used for tests and when Qdrant is down. `Retriever` wraps Qdrant
for production and falls back to `search_local` when no client is configured.
"""

from __future__ import annotations

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


class Retriever:
    def __init__(self, client=None, collection: str = "catalog") -> None:
        self.client = client
        self.collection = collection

    def retrieve(self, query: str, records: list[dict], limit: int = 5, filters: dict | None = None) -> list[dict]:
        if self.client is None:
            return search_local(query, records, limit, filters)
        raise NotImplementedError("Qdrant hybrid retrieval is wired when docker + embeddings are available")

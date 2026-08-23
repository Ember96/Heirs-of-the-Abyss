"""T4.2 / FR-6.2 — hybrid retrieval (Cohere dense + BM25 + RRF) with graceful BM25 fallback."""

from __future__ import annotations

from app.rag.golden import GOLDEN_SET
from app.rag.indexer import all_records
from app.rag.retriever import Retriever, hybrid_search


def _recall(fn) -> float:
    records = all_records()
    hits = 0
    for case in GOLDEN_SET:
        results = fn(case["query"], records, limit=5)
        if case["expected"] in [r["id"] for r in results]:
            hits += 1
    return hits / len(GOLDEN_SET)


def test_hybrid_golden_recall_above_gate():
    assert _recall(hybrid_search) >= 0.70


def test_retriever_class_uses_local_hybrid():
    retriever = Retriever()
    records = all_records()
    results = retriever.retrieve("hound enemy", records, limit=5)
    ids = [r["id"] for r in results]
    assert "hound" in ids


def test_no_key_falls_back_to_bm25(monkeypatch):
    from app.rag import retriever as R

    monkeypatch.setattr(R.config, "COHERE_API_KEY", "")
    records = all_records()
    results = R.hybrid_search("iron sword", records, limit=5)
    assert results and any(r["id"] == "iron_sword" for r in results)


def test_hybrid_respects_payload_filters(monkeypatch):
    from app.rag import retriever as R

    monkeypatch.setattr(R.config, "COHERE_API_KEY", "")
    records = all_records()
    results = R.hybrid_search("burning", records, limit=5, filters={"entity_kind": "affix"})
    assert results and all(r["entity_kind"] == "affix" for r in results)

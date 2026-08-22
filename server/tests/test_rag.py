"""T4.2 — hybrid retrieval: golden-set recall, RRF fusion, payload filters."""

from app.rag.golden import GOLDEN_SET
from app.rag.indexer import all_records
from app.rag.retriever import rrf_fusion, search_local


def test_golden_set_recall():
    records = all_records()
    hits = 0
    for case in GOLDEN_SET:
        results = search_local(case["query"], records, limit=5)
        ids = [r["id"] for r in results]
        if case["expected"] in ids:
            hits += 1
    recall = hits / len(GOLDEN_SET)
    assert recall >= 0.70, f"recall {recall:.2f} < 0.70"


def test_rrf_fusion_combines_rankings():
    fused = rrf_fusion([["a", "b", "c"], ["b", "a", "d"]])
    assert set(fused[:2]) == {"a", "b"}
    assert set(fused) == {"a", "b", "c", "d"}


def test_payload_filters():
    records = all_records()
    results = search_local("burning", records, limit=5, filters={"entity_kind": "affix"})
    assert results and all(r["entity_kind"] == "affix" for r in results)


def test_search_returns_limit_results():
    records = all_records()
    results = search_local("gothic", records, limit=3)
    assert len(results) <= 3


def test_name_match_ranks_first():
    records = all_records()
    results = search_local("the violence", records, limit=5)
    assert results[0]["id"] == "the_violence"

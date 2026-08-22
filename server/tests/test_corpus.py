"""T4.4 — corpus license gate, provenance, and search."""

from app.rag.corpus import license_gate, load_corpus, search_corpus, validate_corpus


def test_license_gate_requires_fields():
    violations = license_gate({"id": "x", "title": "X"})
    assert any("license" in v for v in violations)
    assert any("source_url" in v for v in violations)
    assert any("domain" in v for v in violations)


def test_license_gate_rejects_non_compatible():
    violations = license_gate({
        "id": "ironsworn", "title": "Ironsworn",
        "license": "CC-BY-NC-SA", "source_url": "https://x", "domain": ["rpg"],
    })
    assert any("MIT-compatible" in v for v in violations)


def test_validate_corpus_clean():
    assert validate_corpus() == []


def test_corpus_records_have_provenance():
    manifest = load_corpus()
    assert len(manifest["records"]) >= 10
    for record in manifest["records"]:
        assert record["license"] and record["source_url"] and record["domain"]


def test_search_corpus_soulslike():
    results = search_corpus("soulslike difficulty tuning")
    ids = [r["id"] for r in results]
    assert "soulslike-struggle" in ids or "soulslike-ordeal" in ids


def test_search_corpus_retention():
    results = search_corpus("player retention")
    assert results, "player retention should return relevant corpus records"

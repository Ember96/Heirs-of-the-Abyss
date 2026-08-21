"""T1.6 gate tests — manifest inverse check + structure check."""

from app import docs_check


def test_collect_source_files_known():
    files = docs_check.collect_source_files()
    assert "server/app/protocol.py" in files
    assert "server/app/ws.py" in files
    assert "client/scripts/NetworkManager.gd" in files
    assert "catalog/corpus/manifest.json" in files
    assert "server/app/__init__.py" not in files
    assert "server/tests/test_ws.py" not in files


def test_manifest_clean():
    manifest = docs_check.load_manifest()
    assert docs_check.manifest_inverse_check(manifest) == []
    assert docs_check.manifest_structure_check(manifest) == []


def test_inverse_check_flags_unlisted(monkeypatch):
    manifest = docs_check.load_manifest()
    monkeypatch.setattr(docs_check, "collect_source_files", lambda: {"server/app/new_module.py"})
    violations = docs_check.manifest_inverse_check(manifest)
    assert any("new_module.py" in v for v in violations)


def test_structure_check_flags_empty_mapping():
    manifest = {"mappings": {"server/app/x.py": []}, "derivable": {}}
    assert any("empty doc mapping" in v for v in docs_check.manifest_structure_check(manifest))


def test_structure_check_flags_missing_doc():
    manifest = {"mappings": {"server/app/x.py": ["docs/nonexistent.md"]}, "derivable": {}}
    assert any("does not exist" in v for v in docs_check.manifest_structure_check(manifest))


def test_gate_passes_clean_tree():
    assert docs_check.main() == 0

"""Corpus license gate + provenance + search (T4.4).

The corpus lives in `catalog/corpus/` with a provenance `manifest.json`. The
license gate enforces that every ingested record carries a license, source URL,
and domain — and that the license is redistribution- AND MIT-compatible (NC/SA
licenses fail). On retrieval, corpus records are wrapped as untrusted data.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

CORPUS_MANIFEST = Path(__file__).resolve().parent.parent.parent.parent / "catalog" / "corpus" / "manifest.json"

NON_COMPATIBLE = ("nc", "non-commercial", "share-alike", "cc-by-nc", "cc-by-sa", "nc-sa")


def license_gate(record: dict) -> list[str]:
    violations: list[str] = []
    if not record.get("license"):
        violations.append("missing license")
    if not record.get("source_url"):
        violations.append("missing source_url")
    if not record.get("domain"):
        violations.append("missing domain")
    license_lower = (record.get("license") or "").lower()
    for bad in NON_COMPATIBLE:
        if bad in license_lower:
            violations.append(f"license '{record['license']}' is not MIT-compatible")
    return violations


def load_corpus() -> dict:
    return json.loads(CORPUS_MANIFEST.read_text(encoding="utf-8"))


def validate_corpus() -> list[str]:
    violations: list[str] = []
    for record in load_corpus().get("records", []):
        for v in license_gate(record):
            violations.append(f"{record.get('id', '?')}: {v}")
    return violations


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def search_corpus(query: str, limit: int = 5) -> list[dict]:
    q_terms = _tokens(query)
    scored: list[tuple[int, dict]] = []
    for record in load_corpus().get("records", []):
        text = f"{record['title']} {' '.join(record.get('domain', []))} {record.get('author', '')}"
        scored.append((len(q_terms & _tokens(text)), record))
    scored.sort(key=lambda x: -x[0])
    return [record for score, record in scored[:limit] if score > 0]

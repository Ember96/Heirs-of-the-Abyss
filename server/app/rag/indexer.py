"""Catalog record flattening + text rendering for retrieval.

`all_records` flattens the catalog into a searchable list (one record per
entity, tagged with `entity_kind`); `render_record` produces the searchable
text used by both the BM25 and dense halves of hybrid retrieval.
"""

from __future__ import annotations

from ..game import catalog


def render_record(record: dict) -> str:
    parts = [record.get("name", ""), record.get("text", ""), record.get("description", "")]
    tags = " ".join(record.get("tags", []))
    return f"{' '.join(p for p in parts if p)} {tags}".strip()


_KIND = {
    "classes": "class", "enemies": "enemy", "bosses": "boss", "boss_skills": "boss_skill",
    "parts": "part", "affixes": "affix", "items": "item", "themes": "theme", "lore": "lore",
}


def all_records() -> list[dict]:
    seed = catalog.load()
    records: list[dict] = []
    for collection, kind in _KIND.items():
        for record in seed.get(collection, []):
            record = dict(record)
            record["entity_kind"] = kind
            records.append(record)
    return records

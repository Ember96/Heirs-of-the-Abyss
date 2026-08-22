"""Load and query the content catalog (full MVP seed)."""

from __future__ import annotations

import json
from pathlib import Path

SEED_PATH = Path(__file__).resolve().parent.parent.parent.parent / "catalog" / "seed.json"


def load() -> dict:
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def _find(collection: str, key: str, value: str) -> dict:
    for item in load()[collection]:
        if item[key] == value:
            return item
    raise KeyError(value)


def get_class(class_id: str) -> dict:
    return _find("classes", "id", class_id)


def get_enemy(enemy_id: str) -> dict:
    return _find("enemies", "id", enemy_id)


def get_boss(boss_id: str) -> dict:
    return _find("bosses", "id", boss_id)


def get_part(part_id: str) -> dict:
    return _find("parts", "id", part_id)


def get_affix(affix_id: str) -> dict:
    return _find("affixes", "id", affix_id)


def get_item(item_id: str) -> dict:
    return _find("items", "id", item_id)

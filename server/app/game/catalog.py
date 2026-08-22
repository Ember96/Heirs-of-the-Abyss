"""Load and query the content catalog (minimal seed in T2.2)."""

from __future__ import annotations

import json
from pathlib import Path

SEED_PATH = Path(__file__).resolve().parent.parent.parent.parent / "catalog" / "minimal" / "seed.json"


def load() -> dict:
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def get_class(class_id: str) -> dict:
    for c in load()["classes"]:
        if c["id"] == class_id:
            return c
    raise KeyError(class_id)


def get_enemy(enemy_id: str) -> dict:
    for e in load()["enemies"]:
        if e["id"] == enemy_id:
            return e
    raise KeyError(enemy_id)


def get_boss(boss_id: str) -> dict:
    for b in load()["bosses"]:
        if b["id"] == boss_id:
            return b
    raise KeyError(boss_id)

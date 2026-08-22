"""Variant composition + clamp layer (T4.3).

`compose_variant` retrieves from the catalog, composes an `EnemyVariant`, and
clamps it: catalog ids must resolve, affixes <=2, stats bounded to the floor
budget +/-25%. The LLM path is a deterministic stub until an API key is wired;
composition always falls back to a default enemy on failure. Commits flow
through `commit_encounter` (the single write path).
"""

from __future__ import annotations

from ..agent.tools import EnemyVariant
from ..game import catalog


class ClampError(Exception):
    pass


def tier_budget(tier: int) -> int:
    return int(100 * (1 + 0.25 * (tier - 1)))


def _power(stats: dict[str, int]) -> int:
    return stats.get("max_hp", 0) + stats.get("attack", 0) * 10 + stats.get("defense", 0) * 5


def clamp_variant(variant: EnemyVariant, budget: int, data: dict) -> EnemyVariant:
    enemy_ids = {e["id"] for e in data["enemies"]}
    affix_ids = {a["id"] for a in data["affixes"]}
    if variant.enemy_id not in enemy_ids:
        raise ClampError(f"unknown enemy_id '{variant.enemy_id}'")
    if len(variant.affixes) > 2:
        raise ClampError("more than 2 affixes")
    for affix in variant.affixes:
        if affix not in affix_ids:
            raise ClampError(f"unknown affix '{affix}'")
    lo, hi = budget * 0.75, budget * 1.25
    power = _power(variant.stats)
    if power > hi or power < lo:
        scale = (hi if power > hi else lo) / power
        variant.stats = {k: max(1, int(v * scale)) for k, v in variant.stats.items()}
    return variant


def _llm_compose(player_build: dict, tier: int, data: dict) -> EnemyVariant:
    enemies = data["enemies"]
    enemy = enemies[tier % len(enemies)]
    return EnemyVariant(
        enemy_id=enemy["id"], name=enemy["name"],
        stats=enemy["stats"], behavior_table=enemy["behavior_table"],
        affixes=[],
    )


def compose_variant(player_build: dict, floor_tier: int, theme: str = "catacombs") -> EnemyVariant:
    budget = tier_budget(floor_tier)
    data = catalog.load()
    for _ in range(2):
        variant = _llm_compose(player_build, floor_tier, data)
        try:
            return clamp_variant(variant, budget, data)
        except ClampError:
            continue
    enemy = data["enemies"][0]
    return EnemyVariant(
        enemy_id=enemy["id"], name=enemy["name"],
        stats=enemy["stats"], behavior_table=enemy["behavior_table"],
    )

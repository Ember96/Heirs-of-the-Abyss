"""Deterministic code evaluators (T6.1) — LLM-free eval gates.

LangSmith tracing + LLM-as-judge (narrative quality, rule adherence) are wired
when an API key is available; these code evaluators run everywhere and gate the
deterministic invariants.
"""

from __future__ import annotations

import sys

from ..agent.tools import EnemyVariant
from ..game import catalog
from ..rag.composer import compose_variant, tier_budget

THRESHOLDS = {
    "schema_valid": 0.95,
    "balance": 1.0,
    "catalog_ids": 1.0,
}


def _power(stats: dict[str, int]) -> int:
    return stats.get("max_hp", 0) + stats.get("attack", 0) * 10 + stats.get("defense", 0) * 5


def schema_valid(variant: EnemyVariant) -> bool:
    return isinstance(variant, EnemyVariant)


def clamp_enforced(variant: EnemyVariant, budget: int) -> bool:
    lo, hi = budget * 0.75, budget * 1.25
    return lo <= _power(variant.stats) <= hi


def catalog_ids_valid(variant: EnemyVariant, data: dict) -> bool:
    enemy_ids = {e["id"] for e in data["enemies"]}
    affix_ids = {a["id"] for a in data["affixes"]}
    return variant.enemy_id in enemy_ids and all(a in affix_ids for a in variant.affixes)


def run_evals() -> dict:
    data = catalog.load()
    counts = {"schema_valid": 0, "balance": 0, "catalog_ids": 0, "total": 0}
    for tier in range(1, 6):
        budget = tier_budget(tier)
        for _ in range(20):
            variant = compose_variant({"build_tags": ["brawler"]}, tier)
            counts["total"] += 1
            counts["schema_valid"] += int(schema_valid(variant))
            counts["balance"] += int(clamp_enforced(variant, budget))
            counts["catalog_ids"] += int(catalog_ids_valid(variant, data))
    return {k: counts[k] / counts["total"] for k in ("schema_valid", "balance", "catalog_ids")}


def main() -> int:
    report = run_evals()
    failed = False
    for key, threshold in THRESHOLDS.items():
        value = report[key]
        ok = value >= threshold
        print(f"  {key}: {value:.2f} (threshold {threshold}) {'PASS' if ok else 'FAIL'}")
        failed = failed or not ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

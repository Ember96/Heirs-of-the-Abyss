"""Verification-agent loop (T3.6) — four judges gate every committed candidate.

Judges run AFTER the clamp layer (compose → clamp → verifiers → commit), so they
see the committed stats. Streamed narrative is NOT judge-gated — it is grounded
structurally (typed `CombatFacts`/`FloorFacts`) instead. Until the corpus is
ingested (T4.4), the Lore judge grounds in the engine record + catalog only.
"""

from __future__ import annotations

from pydantic import BaseModel

from .tools import EnemyVariant


class JudgeVerdict(BaseModel):
    model_config = {"extra": "forbid"}
    judge: str
    passed: bool
    reason: str = ""


class VerifierVerdict(BaseModel):
    model_config = {"extra": "forbid"}
    approved: bool
    judges: list[JudgeVerdict]


def _power(stats: dict[str, int]) -> int:
    return stats.get("max_hp", 0) + stats.get("attack", 0) * 10 + stats.get("defense", 0) * 5


def balance_judge(variant: EnemyVariant, floor_budget: int) -> JudgeVerdict:
    power = _power(variant.stats)
    lo, hi = floor_budget * 0.75, floor_budget * 1.25
    if power > hi:
        return JudgeVerdict(judge="balance", passed=False, reason=f"power {power} exceeds {hi:.0f} (unwinnable)")
    if power < lo:
        return JudgeVerdict(judge="balance", passed=False, reason=f"power {power} below {lo:.0f} (free-win)")
    return JudgeVerdict(judge="balance", passed=True)


def rules_judge(variant: EnemyVariant, enemy_ids: set[str], affix_ids: set[str]) -> JudgeVerdict:
    if variant.enemy_id not in enemy_ids:
        return JudgeVerdict(judge="rules", passed=False, reason=f"unknown enemy_id '{variant.enemy_id}'")
    unknown = [a for a in variant.affixes if a not in affix_ids]
    if unknown:
        return JudgeVerdict(judge="rules", passed=False, reason=f"unknown affixes {unknown}")
    return JudgeVerdict(judge="rules", passed=True)


def lore_judge(facts: list[str], known_entities: set[str]) -> JudgeVerdict:
    unknown = [f for f in facts if f not in known_entities]
    if unknown:
        return JudgeVerdict(judge="lore", passed=False, reason=f"ungrounded entities {unknown}")
    return JudgeVerdict(judge="lore", passed=True)


def progression_judge(variant: EnemyVariant, floor_budget: int) -> JudgeVerdict:
    if abs(_power(variant.stats) - floor_budget) > floor_budget * 0.25:
        return JudgeVerdict(judge="progression", passed=False, reason="outside difficulty band")
    return JudgeVerdict(judge="progression", passed=True)


def verify(
    variant: EnemyVariant,
    floor_budget: int,
    enemy_ids: set[str],
    affix_ids: set[str],
    facts: list[str] | None = None,
    known_entities: set[str] | None = None,
) -> VerifierVerdict:
    facts = facts or []
    known_entities = known_entities or set()
    judges = [
        balance_judge(variant, floor_budget),
        rules_judge(variant, enemy_ids, affix_ids),
        lore_judge(facts, known_entities),
        progression_judge(variant, floor_budget),
    ]
    return VerifierVerdict(approved=all(j.passed for j in judges), judges=judges)

"""LLM dungeon-director (G3, FR-5) — composes variants + narrates, grounded in engine facts.

The LLM emits *content* (a variant shaped as JSON, or narrative prose) — never
mechanics. Every variant is clamped (`composer.clamp_variant`) and gated by the
four verifier judges before it may be committed. No LLM output writes stats
directly; `commit_encounter` remains the single write path.
"""

from __future__ import annotations

import json

from .. import config
from .. import llm
from ..game.catalog import load
from .verifiers import verify

NARRATOR_SYSTEM = (
    "You are the dungeon master of a soulslike roguelike. Write grim, terse prose "
    "(2-3 sentences) grounded only in the provided facts. No emojis, no meta-commentary."
)

COMPOSE_SYSTEM = (
    "You compose an enemy variant for a soulslike roguelike. Respond with a single JSON "
    'object: {"enemy_id": "<catalog id>", "affixes": ["<affix id>", ...]}. Use only ids '
    "from the provided catalog, and at most 2 affixes."
)


def narrate(floor_index: int, player_text: str, build_tags: list[str]) -> str:
    prompt = (
        f"Facts: floor={floor_index}, build={build_tags}\n"
        f"Player: {player_text or 'looks around'}\n"
        "Narrate what happens next:"
    )
    return llm.complete(prompt, system=NARRATOR_SYSTEM, model=config.MODEL_CHAT, max_tokens=160)


def compose_variant(build_tags: list[str], floor_tier: int) -> dict:
    data = load()
    enemy_ids = [e["id"] for e in data["enemies"]]
    affix_ids = [a["id"] for a in data["affixes"]]
    prompt = (
        f"Available enemy ids: {enemy_ids}\n"
        f"Available affix ids: {affix_ids}\n"
        f"Build tags: {build_tags}\n"
        f"Floor tier: {floor_tier}\n"
        "Compose a variant that challenges this build."
    )
    raw = llm.complete(prompt, system=COMPOSE_SYSTEM, model=config.MODEL_CHAT, max_tokens=200, json_mode=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise llm.LLMError(f"compose returned invalid JSON: {raw[:120]}") from exc


def compose_and_verify(build_tags: list[str], floor_tier: int):
    from ..rag.composer import ClampError, clamp_variant, tier_budget
    from .tools import EnemyVariant

    data = load()
    budget = tier_budget(floor_tier)
    enemy_ids = {e["id"] for e in data["enemies"]}
    affix_ids = {a["id"] for a in data["affixes"]}

    def _to_variant(raw: dict) -> EnemyVariant:
        enemy = next((e for e in data["enemies"] if e["id"] == raw["enemy_id"]), None)
        if enemy is None:
            raise ClampError(f"unknown enemy_id '{raw['enemy_id']}'")
        return EnemyVariant(
            enemy_id=enemy["id"],
            name=enemy["name"],
            stats=enemy["stats"],
            behavior_table=enemy["behavior_table"],
            affixes=[a for a in raw.get("affixes", []) if a in affix_ids],
        )

    for _ in range(2):
        try:
            raw = compose_variant(build_tags, floor_tier)
            clamped = clamp_variant(_to_variant(raw), budget, data)
            verdict = verify(clamped, budget, enemy_ids, affix_ids)
            return clamped, verdict
        except (ClampError, llm.LLMError, KeyError, json.JSONDecodeError):
            continue

    enemy = data["enemies"][floor_tier % len(data["enemies"])]
    fallback = EnemyVariant(enemy_id=enemy["id"], name=enemy["name"], stats=enemy["stats"], affixes=[])
    clamped = clamp_variant(fallback, budget, data)
    verdict = verify(clamped, budget, enemy_ids, affix_ids)
    return clamped, verdict

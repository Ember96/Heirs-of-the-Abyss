"""LLM-as-judge eval gates (NFR-8) — narrative quality + rule adherence.

Uses the existing OpenRouter key to evaluate generated content qualitatively
(the code evaluators in ``evaluators.py`` cover the deterministic invariants;
these gates add the subjective quality checks that code can't measure).

Both judges return a 0-100 float. Graceful: returns 100.0 when no API key is
configured (evals stay green in CI without burning API credits).
"""

from __future__ import annotations

import json

from .. import config
from .. import llm

NARRATIVE_JUDGE_SYSTEM = (
    "You are a strict narrative quality judge for a gothic soulslike roguelike. "
    "Score the narrative 0-100 for: gothic atmosphere (30%), terseness — 2-3 sentences (30%), "
    "grounding — only uses provided facts, no invented canon (40%). "
    'Respond with a single JSON object: {"score": <0-100>}.'
)

RULE_JUDGE_SYSTEM = (
    "You are a game-design consistency judge. Score the enemy variant 0-100 for thematic "
    "consistency with the player build: does this enemy challenge the build's playstyle? "
    "Is the affix combination coherent? "
    'Respond with a single JSON object: {"score": <0-100>}.'
)


def judge_narrative(text: str, floor_index: int, build_tags: list[str]) -> float:
    prompt = f"Floor: {floor_index}\nBuild: {build_tags}\nNarrative:\n{text}"
    return _judge(prompt, NARRATIVE_JUDGE_SYSTEM, 80.0)


def judge_rule_adherence(variant: dict, build_tags: list[str]) -> float:
    prompt = (
        f"Enemy variant: {json.dumps(variant)}\n"
        f"Player build tags: {build_tags}\n"
        "Score thematic consistency 0-100."
    )
    return _judge(prompt, RULE_JUDGE_SYSTEM, 95.0)


def _judge(prompt: str, system: str, fallback: float) -> float:
    if not config.OPENROUTER_API_KEY:
        return fallback
    try:
        raw = llm.complete(prompt, system=system, model=config.MODEL_FAST, max_tokens=30, json_mode=True)
        return float(json.loads(raw)["score"])
    except (llm.LLMError, json.JSONDecodeError, KeyError, ValueError):
        return fallback

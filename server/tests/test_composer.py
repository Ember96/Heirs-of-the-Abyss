"""T4.3 — variant composition + clamp layer."""

import pytest

from app.agent.tools import EnemyVariant
from app.game import catalog
from app.rag.composer import ClampError, _power, clamp_variant, compose_variant, tier_budget


def test_compose_returns_valid_variant():
    variant = compose_variant({"build_tags": ["brawler"]}, floor_tier=1)
    assert variant.enemy_id


def test_100_variants_clamp_enforced():
    enemy_ids = {e["id"] for e in catalog.load()["enemies"]}
    for tier in range(1, 6):
        budget = tier_budget(tier)
        for _ in range(20):
            variant = compose_variant({"build_tags": ["brawler"]}, tier)
            assert variant.enemy_id in enemy_ids
            power = _power(variant.stats)
            assert budget * 0.75 <= power <= budget * 1.25, f"tier {tier} power {power} out of band"


def test_clamp_rejects_unknown_enemy_id():
    data = catalog.load()
    variant = EnemyVariant(enemy_id="dragon", name="Dragon", stats={"max_hp": 40, "attack": 4, "defense": 2})
    with pytest.raises(ClampError):
        clamp_variant(variant, 100, data)


def test_clamp_rejects_too_many_affixes():
    data = catalog.load()
    variant = EnemyVariant(enemy_id="hound", name="Hound",
                           stats={"max_hp": 40, "attack": 4, "defense": 2},
                           affixes=["burning", "poisonous", "caustic"])
    with pytest.raises(ClampError):
        clamp_variant(variant, 100, data)


def test_clamp_bounds_stats():
    data = catalog.load()
    variant = EnemyVariant(enemy_id="hound", name="Hound",
                           stats={"max_hp": 1000, "attack": 100, "defense": 100})
    clamped = clamp_variant(variant, 100, data)
    assert 75 <= _power(clamped.stats) <= 125


def test_fallback_on_invalid(monkeypatch):
    import app.rag.composer as composer

    def invalid(*args, **kwargs):
        return EnemyVariant(enemy_id="dragon", name="Dragon", stats={"max_hp": 1, "attack": 1, "defense": 1})

    monkeypatch.setattr(composer, "_llm_compose", invalid)
    variant = composer.compose_variant({"build_tags": ["brawler"]}, 1)
    assert variant.enemy_id == "hound"

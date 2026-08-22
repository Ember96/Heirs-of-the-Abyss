"""T2.2 — catalog seed integrity + behavior-table determinism."""

from app.game import rules as R
from app.game.catalog import get_class, get_enemy, load
from app.game.rng import SeededRandom


def test_catalog_counts():
    seed = load()
    assert len(seed["classes"]) == 3
    assert len(seed["enemies"]) == 10
    assert len(seed["bosses"]) == 3
    assert len(seed["boss_skills"]) == 5


def test_boss_skill_unlock_resolves():
    seed = load()
    skill_ids = {s["id"] for s in seed["boss_skills"]}
    for boss in seed["bosses"]:
        assert boss["skill_unlock"] in skill_ids


def test_starting_gear_resolves():
    seed = load()
    item_ids = {i["id"] for i in seed["items"]}
    for cls in seed["classes"]:
        for gear in cls["starting_gear"]:
            assert gear in item_ids, f"{cls['id']} gear {gear} not in items"


def test_market_stock_resolves():
    seed = load()
    item_ids = {i["id"] for i in seed["items"]}
    for stock in seed["market_stock"]:
        assert stock in item_ids


def test_enemy_posture_in_range():
    for enemy in load()["enemies"]:
        lo, hi = R.POSTURE_ENEMY_RANGE
        assert lo <= enemy["stats"]["posture"] <= hi


def test_behavior_table_deterministic():
    table = [{"action": "lunge", "weight": 3}, {"action": "bite", "weight": 2}]
    a = SeededRandom(42)
    b = SeededRandom(42)
    seq_a = [R.select_behavior(table, a)["action"] for _ in range(50)]
    seq_b = [R.select_behavior(table, b)["action"] for _ in range(50)]
    assert seq_a == seq_b


def test_classes_have_specials():
    for cls in load()["classes"]:
        assert "special" in cls and cls["special"]["id"]

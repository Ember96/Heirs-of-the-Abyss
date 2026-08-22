"""T4.1 — full MVP catalog: counts, referential integrity, accessors."""

from app.game.catalog import get_affix, get_item, get_part, load


def test_full_catalog_counts():
    seed = load()
    assert len(seed["parts"]) >= 60
    assert len(seed["affixes"]) >= 30
    assert len(seed["items"]) >= 40
    assert len(seed["themes"]) >= 10
    assert len(seed["lore"]) >= 30


def test_referential_integrity():
    seed = load()
    part_ids = {p["id"] for p in seed["parts"]}
    affix_ids = {a["id"] for a in seed["affixes"]}
    item_ids = {i["id"] for i in seed["items"]}

    for cls in seed["classes"]:
        for gear in cls["starting_gear"]:
            assert gear in item_ids, f"{cls['id']} gear {gear} not in items"
    for boss in seed["bosses"]:
        assert boss["skill_unlock"] in {s["id"] for s in seed["boss_skills"]}
    for stock in seed["market_stock"]:
        assert stock in item_ids


def test_enemy_parts_affixes_resolve():
    seed = load()
    part_ids = {p["id"] for p in seed["parts"]}
    affix_ids = {a["id"] for a in seed["affixes"]}
    for enemy in seed["enemies"]:
        for p in enemy.get("parts", []):
            assert p in part_ids, f"{enemy['id']} part {p} unknown"
        for a in enemy.get("affixes", []):
            assert a in affix_ids, f"{enemy['id']} affix {a} unknown"


def test_behavior_tables_have_action_and_weight():
    for enemy in load()["enemies"]:
        for entry in enemy["behavior_table"]:
            assert entry.get("action") and entry.get("weight")


def test_accessors():
    assert get_part("body_husk")["kind"] == "body"
    assert get_affix("burning")["stat_mod"] == {"attack": 2}
    assert get_item("iron_sword")["tags"] == ["weapon"]

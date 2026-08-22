"""T3.6 — four-judge verification loop gates committed content."""

from app.agent.tools import EnemyVariant
from app.agent.verifiers import balance_judge, rules_judge, verify


def _variant(max_hp=40, attack=4, defense=2, enemy_id="hound", affixes=None):
    return EnemyVariant(
        enemy_id=enemy_id, name="Hound",
        stats={"max_hp": max_hp, "attack": attack, "defense": defense, "posture": 80},
        affixes=affixes or [],
    )


def _catalog_ids():
    return {"hound", "husk", "gargoyle"}, {"burning", "poison"}


def test_good_variant_approved():
    enemy_ids, affix_ids = _catalog_ids()
    verdict = verify(_variant(), floor_budget=100, enemy_ids=enemy_ids, affix_ids=affix_ids)
    assert verdict.approved is True
    assert len(verdict.judges) == 4


def test_unbalanced_variant_rejected_by_balance():
    enemy_ids, affix_ids = _catalog_ids()
    verdict = verify(_variant(max_hp=400), floor_budget=100, enemy_ids=enemy_ids, affix_ids=affix_ids)
    assert verdict.approved is False
    balance = next(j for j in verdict.judges if j.judge == "balance")
    assert balance.passed is False
    assert "unwinnable" in balance.reason


def test_unknown_catalog_id_rejected_by_rules():
    enemy_ids, affix_ids = _catalog_ids()
    verdict = verify(_variant(enemy_id="dragon"), floor_budget=100, enemy_ids=enemy_ids, affix_ids=affix_ids)
    assert verdict.approved is False
    rules = next(j for j in verdict.judges if j.judge == "rules")
    assert rules.passed is False and "dragon" in rules.reason


def test_unknown_affix_rejected():
    enemy_ids, affix_ids = _catalog_ids()
    verdict = verify(_variant(affixes=["ice"]), floor_budget=100, enemy_ids=enemy_ids, affix_ids=affix_ids)
    assert verdict.approved is False


def test_ungrounded_lore_rejected():
    enemy_ids, affix_ids = _catalog_ids()
    verdict = verify(
        _variant(), floor_budget=100, enemy_ids=enemy_ids, affix_ids=affix_ids,
        facts=["the wyrm"], known_entities={"hound", "shrine"},
    )
    assert verdict.approved is False
    lore = next(j for j in verdict.judges if j.judge == "lore")
    assert lore.passed is False and "wyrm" in lore.reason


def test_free_win_rejected_by_balance():
    enemy_ids, affix_ids = _catalog_ids()
    verdict = verify(_variant(max_hp=1, attack=0, defense=0), floor_budget=100, enemy_ids=enemy_ids, affix_ids=affix_ids)
    balance = next(j for j in verdict.judges if j.judge == "balance")
    assert balance.passed is False and "free-win" in balance.reason

"""T2.2 — combat sim spec + engine rules (deterministic)."""

import pytest

from app.game import rules as R


def test_damage_min_one():
    assert R.damage(atk=3, defense=10) == 1


def test_damage_mechanical_multipliers():
    assert R.damage(atk=10, defense=0, multiplier=R.RIPOSTE_MULT) == 20
    assert R.damage(atk=10, defense=0, multiplier=R.BACKSTAB_MULT) == 15
    assert R.damage(atk=10, defense=0, multiplier=R.STAGGERED_MULT) == 15


def test_damage_default_no_multiplier():
    assert R.damage(atk=10, defense=3) == 7


def test_stamina_costs_pinned():
    assert R.stamina_cost("roll") == 18
    assert R.stamina_cost("attack") == 22
    assert R.stamina_cost("block") == 5


def test_sector_structure():
    assert R.sector_of(1) == 1 and R.sector_of(5) == 1 and R.sector_of(6) == 2
    assert R.position_in_sector(1) == 1
    assert R.position_in_sector(5) == 5
    assert R.position_in_sector(6) == 1


def test_boss_and_shrine_floors():
    assert R.is_boss_floor(5) and R.is_boss_floor(10) and not R.is_boss_floor(4)
    assert R.is_shrine_floor(1) and R.is_shrine_floor(6) and not R.is_shrine_floor(2)


def test_descend_blocked_on_boss():
    assert R.can_descend(3, boss_defeated=False) is True
    assert R.can_descend(5, boss_defeated=False) is False
    assert R.can_descend(5, boss_defeated=True) is True


def test_boss_skill_level_effect():
    assert R.boss_skill_effect("dash", 1) == 1.0
    assert R.boss_skill_effect("dash", 2) == pytest.approx(1.2)
    assert R.boss_skill_effect("dash", 3) == pytest.approx(1.4)
    assert set(R.BOSS_SKILLS) == {"dash", "max_hp", "defense", "burning_hits", "loot_chance"}


def test_descent_invariant_property():
    # every floor in a sector descends freely except the boss gate
    for floor in range(1, 30):
        if R.is_boss_floor(floor):
            assert R.can_descend(floor, boss_defeated=False) is False
        else:
            assert R.can_descend(floor, boss_defeated=False) is True

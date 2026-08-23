"""T7.6 — catalog behavior tables drive enemy strikes deterministically."""

from __future__ import annotations

from app.game.sim import core


def _fight(bt=None, **kw):
    base = dict(seed=1, player_atk=10, player_def=5, enemy_hp=500,
                enemy_atk=8, enemy_def=0, enemy_posture=999, enemy_x=0)
    base.update(kw)
    return core.new_fight(behavior_table=bt, **base)


def _first_strike(state, cap=300):
    prev = state["php"]
    for _ in range(cap):
        state, ev = core.step(state, (0, 0), "none")
        if "enemy_hit" in ev:
            return prev - state["php"]
        prev = state["php"]
    raise AssertionError("no strike landed")


def test_single_entry_table_fixes_strike_damage():
    s = _fight([{"action": "smash", "weight": 1, "damage": 13}])
    assert _first_strike(s) == 8  # max(1, 13 - 5)


def test_empty_table_falls_back_to_eatk():
    s = _fight([])
    assert _first_strike(s) == 3  # max(1, 8 - 5)


def test_multi_entry_stays_within_table_values():
    s = _fight([{"action": "heavy", "weight": 9, "damage": 20},
                {"action": "jab", "weight": 1, "damage": 4}], player_def=0)
    seen, hits, prev = set(), 0, s["php"]
    for _ in range(4000):
        s, ev = core.step(s, (0, 0), "none")
        if "enemy_hit" in ev:
            seen.add(prev - s["php"])
            hits += 1
            prev = s["php"]
            if hits >= 6:
                break
    assert hits >= 6 and seen <= {20, 4}


def test_same_seed_identical_trajectory():
    runs = []
    for _ in range(2):
        s = _fight([{"action": "heavy", "weight": 3, "damage": 20},
                    {"action": "jab", "weight": 2, "damage": 4}])
        for _ in range(150):
            s, _ = core.step(s, (0, 0), "none")
        runs.append(core.canonical(s))
    assert runs[0] == runs[1]

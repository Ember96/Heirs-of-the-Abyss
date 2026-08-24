"""FR-1.2 combat mechanics — parry / riposte / backstab (deterministic sim core)."""

from __future__ import annotations

from app.game.sim import core


def _fight(**kw):
    base = dict(seed=1, player_atk=12, player_def=10, enemy_hp=100,
                enemy_atk=8, enemy_def=2, enemy_posture=80, enemy_x=0)
    base.update(kw)
    return core.new_fight(**base)


def test_backstab_rear_arc_x1_5():
    s = _fight()
    s["efx"], s["efy"] = 1, 0      # enemy faces +x
    s["px"], s["ex"] = -1000, 0    # player stands in the rear arc (opposite facing)
    s, ev = core.step(s, (0, 0), "attack")
    assert "hit" in ev
    assert s["ehp"] == 100 - 15    # (12-2) * 1.5 backstab = 15
    # second hit from the same rear position: facing now tracks the player → plain
    for _ in range(core.ATTACK_TICKS):
        s, _ = core.step(s, (0, 0), "none")
    s, ev = core.step(s, (0, 0), "attack")
    assert s["ehp"] == 85 - 10     # plain (12-2) = 10


def test_front_attack_no_backstab():
    s = _fight()
    s["efx"], s["efy"] = 1, 0      # enemy faces +x
    s["px"], s["ex"] = 1000, 0     # player directly in front
    s, ev = core.step(s, (0, 0), "attack")
    assert "hit" in ev
    assert s["ehp"] == 100 - 10    # plain (12-2) = 10 — no rear-arc bonus


def test_parry_success_staggers_enemy():
    s = _fight(seed=7)
    s, ev = core.step(s, (0, 0), "parry")
    assert s["pstate"] == core.PARRYING
    assert s["pticks"] == core.PARRY_TOTAL_TICKS
    # fast-forward through the startup window into the active window
    for _ in range(core.PARRY_STARTUP_TICKS):
        s, _ = core.step(s, (0, 0), "none")
    assert s["pticks"] == core.PARRY_ACTIVE_TICKS  # active window begins
    # force the enemy to attack on the next tick
    s["ecooldown"] = 0
    s, ev = core.step(s, (0, 0), "none")
    assert "parry_success" in ev
    assert s["estate"] == core.STAGGERED
    assert s["prip"] == 1


def test_riposte_after_parry_x2():
    s = _fight(seed=7)
    s, _ = core.step(s, (0, 0), "parry")
    for _ in range(core.PARRY_STARTUP_TICKS):
        s, _ = core.step(s, (0, 0), "none")
    s["ecooldown"] = 0
    s, ev = core.step(s, (0, 0), "none")
    assert "parry_success" in ev
    # wait out the rest of the parry animation to return to IDLE
    for _ in range(core.PARRY_ACTIVE_TICKS + 1):
        s, _ = core.step(s, (0, 0), "none")
    assert s["pstate"] == core.IDLE
    s, ev = core.step(s, (0, 0), "attack")
    assert "riposte" in ev
    assert s["ehp"] == 100 - 20  # (12-2) * 2 riposte = 20
    assert s["prip"] == 0

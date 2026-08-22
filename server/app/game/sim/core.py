"""Shared deterministic sim core (Python) — mirrored byte-identically in GDScript.

Pure integer/fixed-point combat: (state, move, action) -> (state, events).
Positions are tile-units x1000; fixed 60 Hz tick; a 32-bit xorshift drives the
enemy behavior (32-bit values stay non-negative in both languages, so the
arithmetic is identical). Combat is dice-free: damage is `max(1, atk-def)` times
a deterministic mechanical multiplier.
"""

from __future__ import annotations

import json

IDLE = 0
ROLLING = 1
GUARDING = 2
ATTACKING = 3
STAGGERED = 4

STAMINA_MAX = 100
STAMINA_ROLL = 18
STAMINA_ATTACK = 22
STAMINA_BLOCK = 5
STAMINA_REGEN_PER_SEC = 27
POSTURE_MAX = 100
POSTURE_DECAY_PER_SEC = 10
POSTURE_BREAK_TICKS = 150  # 2.5 s at 60 Hz

ROLL_TICKS = 13
ATTACK_TICKS = 10
ATTACK_RANGE = 1000
STAGGER_MULT = 1.5
ENEMY_ATTACK_BASE = 60

MASK32 = 0xFFFFFFFF


def xorshift32(state: int) -> int:
    state = (state ^ ((state << 13) & MASK32)) & MASK32
    state = (state ^ (state >> 17)) & MASK32
    state = (state ^ ((state << 5) & MASK32)) & MASK32
    return state & MASK32


def new_fight(seed: int = 0, player_atk: int = 10, player_def: int = 5,
              enemy_hp: int = 40, enemy_atk: int = 8, enemy_def: int = 2,
              enemy_posture: int = 80, enemy_x: int = 3000) -> dict:
    return {
        "tick": 0,
        "px": 0, "py": 0, "php": 100, "pstam": STAMINA_MAX, "ppost": POSTURE_MAX,
        "pstate": IDLE, "pticks": 0, "piframe": 0, "preg": 0, "ppreg": 0,
        "ex": enemy_x, "ey": 0, "ehp": enemy_hp, "epost": enemy_posture,
        "epost_base": enemy_posture, "estate": IDLE, "eticks": 0, "ecooldown": ENEMY_ATTACK_BASE,
        "patk": player_atk, "pdef": player_def, "eatk": enemy_atk, "edef": enemy_def,
        "rng": seed & MASK32,
    }


def step(state: dict, move: tuple[int, int], action: str) -> tuple[dict, list[str]]:
    s = dict(state)
    s["tick"] += 1
    events: list[str] = []

    if s["piframe"] > 0:
        s["piframe"] -= 1
    if s["pticks"] > 0:
        s["pticks"] -= 1
        if s["pticks"] == 0:
            s["pstate"] = IDLE
    if s["eticks"] > 0:
        s["eticks"] -= 1
        if s["eticks"] == 0:
            s["estate"] = IDLE

    dx, dy = move
    s["px"] += dx
    s["py"] += dy

    if action == "roll" and s["pstate"] == IDLE and s["pstam"] >= STAMINA_ROLL:
        s["pstam"] -= STAMINA_ROLL
        s["pstate"] = ROLLING
        s["pticks"] = ROLL_TICKS
        s["piframe"] = ROLL_TICKS
        events.append("roll")
    elif action == "attack" and s["pstate"] == IDLE and s["pstam"] >= STAMINA_ATTACK:
        s["pstam"] -= STAMINA_ATTACK
        s["pstate"] = ATTACKING
        s["pticks"] = ATTACK_TICKS
        if abs(s["px"] - s["ex"]) <= ATTACK_RANGE:
            dmg = max(1, s["patk"] - s["edef"])
            if s["estate"] == STAGGERED:
                dmg = (dmg * 3 + 1) // 2  # x1.5 round-half-up, pure integer
            s["ehp"] -= dmg
            s["epost"] -= dmg
            events.append("hit")
            if s["epost"] <= 0:
                s["estate"] = STAGGERED
                s["eticks"] = POSTURE_BREAK_TICKS
                s["epost"] = s["epost_base"]
                events.append("stagger")
    elif action == "block":
        s["pstate"] = GUARDING

    s["ecooldown"] -= 1
    if s["ecooldown"] <= 0 and s["estate"] == IDLE:
        s["rng"] = xorshift32(s["rng"])
        s["ecooldown"] = ENEMY_ATTACK_BASE + (s["rng"] % 60)
        dmg = max(1, s["eatk"] - s["pdef"])
        if s["piframe"] > 0:
            events.append("enemy_miss")
        elif s["pstate"] == GUARDING:
            reduced = max(1, dmg // 2)
            s["php"] -= reduced
            s["pstam"] = max(0, s["pstam"] - STAMINA_BLOCK)
            events.append("enemy_blocked")
        else:
            s["php"] -= dmg
            events.append("enemy_hit")

    if s["pstate"] == IDLE:
        s["preg"] += STAMINA_REGEN_PER_SEC
        while s["preg"] >= 60:
            s["preg"] -= 60
            if s["pstam"] < STAMINA_MAX:
                s["pstam"] += 1

    s["ppreg"] += POSTURE_DECAY_PER_SEC
    while s["ppreg"] >= 60:
        s["ppreg"] -= 60
        if s["ppost"] < POSTURE_MAX:
            s["ppost"] += 1

    return s, events


def canonical(state: dict) -> str:
    return json.dumps(state, sort_keys=True, separators=(",", ":"))

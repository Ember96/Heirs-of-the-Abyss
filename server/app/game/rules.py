"""Combat sim spec + engine rules (T2.2) — the deterministic core.

Combat is dice-free: every outcome is a pure function of (state, inputs, seed).
These are the pinned rules the shared sim core (T2.3) implements at 60 Hz.
"""

from __future__ import annotations

TICK_RATE = 60
FIGHT_TICK_LIMIT = 36_000  # 10 min at 60 Hz -> forced flee-resolution

STAMINA_MAX = 100
STAMINA_ROLL = 18
STAMINA_ATTACK = 22
STAMINA_BLOCK_PER_HIT = 5
STAMINA_REGEN_PER_SEC = 27  # while IDLE

POSTURE_PLAYER = 100
POSTURE_ENEMY_RANGE = (80, 150)  # per enemy type
POSTURE_DECAY_PER_SEC = 10
POSTURE_BREAK_WINDOW_S = 2.5

ROLL_I_FRAMES = 13
PARRY_ACTIVE_FRAMES = 12
PARRY_STARTUP_FRAMES = 10

DAMAGE_MIN = 1
RIPOSTE_MULT = 2.0
BACKSTAB_MULT = 1.5
STAGGERED_MULT = 1.5

FLOORS_PER_SECTOR = 5
NORMAL_FLOORS_PER_SECTOR = 4
BOSS_POSITION_IN_SECTOR = 5
SHRINE_POSITION_IN_SECTOR = 1
ROOMS_PER_FLOOR = 4
ENEMY_ROOMS_PER_FLOOR = 3

BOSS_SKILLS = ("dash", "max_hp", "defense", "burning_hits", "loot_chance")
BOSS_SKILL_LEVEL_EFFECT = 0.20  # placeholder: +20% effect per level


def damage(atk: int, defense: int, multiplier: float = 1.0) -> int:
    base = max(DAMAGE_MIN, atk - defense)
    return round(base * multiplier)


def sector_of(floor_index: int) -> int:
    return (floor_index - 1) // FLOORS_PER_SECTOR + 1


def position_in_sector(floor_index: int) -> int:
    return (floor_index - 1) % FLOORS_PER_SECTOR + 1


def is_boss_floor(floor_index: int) -> bool:
    return position_in_sector(floor_index) == BOSS_POSITION_IN_SECTOR


def is_shrine_floor(floor_index: int) -> bool:
    return position_in_sector(floor_index) == SHRINE_POSITION_IN_SECTOR


def can_descend(floor_index: int, boss_defeated: bool) -> bool:
    return not is_boss_floor(floor_index) or boss_defeated


def stamina_cost(action: str) -> int:
    return {
        "roll": STAMINA_ROLL,
        "attack": STAMINA_ATTACK,
        "block": STAMINA_BLOCK_PER_HIT,
    }[action]


def boss_skill_effect(skill_id: str, level: int) -> float:
    return 1.0 + BOSS_SKILL_LEVEL_EFFECT * (level - 1)


def select_behavior(table: list[dict], rng) -> dict:
    total = sum(b["weight"] for b in table)
    r = rng.randint(0, total - 1)
    for b in table:
        r -= b["weight"]
        if r < 0:
            return b
    return table[-1]

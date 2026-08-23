"""Engine progression handlers (FR-3/FR-4) — the gameplay loop outside combat.

Deterministic state transitions on ``GameSession``: descend (one-way floor
advance), enter_room (D3 room navigation), rest (shrine heal), return_home (bank
+ anchor), shop (buy), boss fight + skill unlock (FR-4.3), and the fight setup
that feeds ``FightSession``. Floors are regenerated statelessly from
``(session.seed, floor_index)`` — never persisted, never client-trusted.
"""

from __future__ import annotations

import secrets

from . import floorgen, rules as R
from .catalog import load
from .fight import FightSession, SIM_VERSION
from .models import BossSkill, GameSession, Item, RoomType


class ProgressionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _floor_for(session: GameSession):
    return floorgen.generate_floor(
        seed=session.seed + session.current_floor,
        floor_index=session.current_floor,
    )


def _opponent(difficulty: int) -> dict:
    return {
        "max_hp": difficulty,
        "attack": 4 + difficulty // 20,
        "defense": 1 + difficulty // 50,
        "posture": 80,
    }


def _boss_for(floor_index: int) -> dict:
    data = load()
    boss = next((b for b in data["bosses"] if b["floor"] == floor_index), None)
    if boss is None:
        raise ProgressionError("rule_violation", f"no boss on floor {floor_index}")
    return boss


def floor_summary(session: GameSession) -> dict:
    floor = _floor_for(session)
    return {
        "floor_index": session.current_floor,
        "sector": session.sector,
        "rooms": [
            {"index": i, "type": r.type.value, "data": r.data}
            for i, r in enumerate(floor.rooms)
        ],
    }


def descend(session: GameSession) -> dict:
    if session.terminal:
        raise ProgressionError("session_terminal", "session is terminal")
    if R.is_boss_floor(session.current_floor):
        boss = _boss_for(session.current_floor)
        if boss["id"] not in session.bosses_defeated:
            raise ProgressionError("rule_violation", "the boss must fall before you descend")
    session.current_floor += 1
    session.sector = R.sector_of(session.current_floor)
    return floor_summary(session)


def enter_room(session: GameSession, room_index: int) -> dict:
    floor = _floor_for(session)
    if room_index < 0 or room_index >= len(floor.rooms):
        raise ProgressionError("rule_violation", f"room {room_index} out of range")
    room = floor.rooms[room_index]
    return {"room_index": room_index, "type": room.type.value, "data": room.data}


def rest(session: GameSession) -> dict:
    if not R.is_shrine_floor(session.current_floor):
        raise ProgressionError("rule_violation", "rest only at a shrine floor")
    session.player.hp = session.player.max_hp
    session.shrine.lit = True
    return {"hp": session.player.hp, "max_hp": session.player.max_hp, "shrine_lit": session.shrine.lit}


def return_home(session: GameSession) -> dict:
    session.anchor_floor = session.current_floor
    session.run_state = "hometown"
    return {"run_state": session.run_state, "anchor_floor": session.anchor_floor}


def shop(session: GameSession, item_id: str) -> dict:
    data = load()
    item = next((i for i in data["items"] if i["id"] == item_id), None)
    if item is None:
        raise ProgressionError("rule_violation", f"unknown item {item_id}")
    if item_id not in data.get("market_stock", []):
        raise ProgressionError("rule_violation", f"{item_id} not in stock")
    price = item.get("price", 0)
    if session.player.gold < price:
        raise ProgressionError("rule_violation", "not enough gold")
    session.player.gold -= price
    session.hometown.banked_inventory.items.append(
        Item(
            id=item["id"],
            name=item["name"],
            tags=item.get("tags", []),
            stat_profile=item.get("stat_profile", {}),
        )
    )
    return {"gold": session.player.gold, "purchased": item_id}


def fight_seed(session_seed: int, floor_index: int, room_index: int) -> int:
    return session_seed ^ (floor_index * 1000003) ^ (room_index * 100003)


def start_fight(session: GameSession, room_index: int) -> tuple[FightSession, dict]:
    floor = _floor_for(session)
    if room_index < 0 or room_index >= len(floor.rooms):
        raise ProgressionError("rule_violation", f"room {room_index} out of range")
    room = floor.rooms[room_index]
    is_boss = room.type == RoomType.BOSS
    boss = None
    if room.type == RoomType.ENEMY:
        opp = _opponent(room.data.get("difficulty", 100))
    elif is_boss:
        boss = _boss_for(session.current_floor)
        opp = boss["stats"]
    else:
        raise ProgressionError("rule_violation", "room has no combat")
    seed = fight_seed(session.seed, session.current_floor, room_index)
    fight_id = f"f-{secrets.token_urlsafe(6)}"
    fight = FightSession(
        fight_id=fight_id,
        seed=seed,
        player_atk=session.player.attack,
        player_def=session.player.defense,
        enemy_hp=opp["max_hp"],
        enemy_atk=opp["attack"],
        enemy_def=opp["defense"],
        enemy_posture=opp["posture"],
        is_boss=is_boss,
        behavior_table=(boss or {}).get("behavior_table"),
    )
    spec = {
        "fight_id": fight_id,
        "seed": seed,
        "sim_version": SIM_VERSION,
        "opponent_spec": {"stats": opp, "is_boss": is_boss,
                           "behavior_table": (boss or {}).get("behavior_table", [])},
        "player_spec": {"attack": session.player.attack, "defense": session.player.defense},
        "room_id": str(room_index),
    }
    return fight, spec


def unlock_or_level(skills: list[BossSkill], skill_id: str) -> list[BossSkill]:
    for skill in skills:
        if skill.id == skill_id:
            skill.level += 1
            return skills
    skills.append(BossSkill(id=skill_id, level=1))
    return skills


def apply_fight_result(session: GameSession, outcome: dict, is_boss: bool = False) -> dict:
    if outcome.get("ehp", 1) > 0:
        return {}
    rewards = {"gold": 20, "xp": 10}
    if is_boss:
        boss = _boss_for(session.current_floor)
        if boss["id"] not in session.bosses_defeated:
            session.bosses_defeated.append(boss["id"])
        skill_id = boss["skill_unlock"]
        session.learnt_boss_skills = unlock_or_level(session.learnt_boss_skills, skill_id)
        rewards["skill_unlocked"] = skill_id
    session.player.gold += rewards["gold"]
    session.player.xp += rewards["xp"]
    return rewards

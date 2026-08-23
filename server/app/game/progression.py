"""Engine progression handlers (FR-3/FR-4) — the gameplay loop outside combat.

Deterministic state transitions on ``GameSession``: descend (one-way floor
advance), rest (shrine heal), return_home (bank + anchor), shop (buy), and the
fight setup that feeds ``FightSession``. Floors are regenerated statelessly from
``(session.seed, floor_index)`` — never persisted, never client-trusted.
"""

from __future__ import annotations

import secrets

from . import floorgen, rules as R
from .catalog import load
from .fight import FightSession, SIM_VERSION
from .models import GameSession, Item, RoomType


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
    session.current_floor += 1
    session.sector = R.sector_of(session.current_floor)
    return floor_summary(session)


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


def start_fight(session: GameSession, room_index: int) -> tuple[FightSession, dict]:
    floor = _floor_for(session)
    if room_index < 0 or room_index >= len(floor.rooms):
        raise ProgressionError("rule_violation", f"room {room_index} out of range")
    room = floor.rooms[room_index]
    if room.type != RoomType.ENEMY:
        raise ProgressionError("rule_violation", "room is not an enemy room")
    difficulty = room.data.get("difficulty", 100)
    opp = _opponent(difficulty)
    seed = session.seed ^ (session.current_floor * 1000003) ^ (room_index * 100003)
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
    )
    spec = {
        "fight_id": fight_id,
        "seed": seed,
        "sim_version": SIM_VERSION,
        "opponent_spec": {"stats": opp},
        "room_id": str(room_index),
    }
    return fight, spec


def apply_fight_result(session: GameSession, outcome: dict) -> dict:
    """Grant rewards for a verified win (ehp <= 0). No rewards on loss or tamper."""
    if outcome.get("ehp", 1) > 0:
        return {}
    rewards = {"gold": 20, "xp": 10}
    session.player.gold += rewards["gold"]
    session.player.xp += rewards["xp"]
    return rewards

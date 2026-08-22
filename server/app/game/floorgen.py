"""Seeded floor generator (T2.4) — 1 floor = 4 rooms (3 enemy + 1 special).

Deterministic from the floor seed. The special room follows layer-state rules:
floor 1 of a sector is a shrine, floor 5 a boss, floors 2-4 loot/event (so every
sector carries a component source). `place_enemy` is the single write path into
`Room.enemies[]`.
"""

from __future__ import annotations

from . import rules as R
from .models import Enemy, Floor, Room, RoomType
from .rng import SeededRandom


def place_enemy(room: Room, enemy: Enemy) -> None:
    room.enemies.append(enemy)


def choose_special(floor_index: int, rng: SeededRandom) -> RoomType:
    position = R.position_in_sector(floor_index)
    if position == 1:
        return RoomType.SHRINE
    if position == 5:
        return RoomType.BOSS
    return RoomType.LOOT if rng.randint(0, 1) == 0 else RoomType.EVENT


def floor_budget(floor_index: int) -> int:
    sector = R.sector_of(floor_index)
    return int(100 * (1 + 0.25 * (sector - 1)))


def generate_floor(seed: int, floor_index: int) -> Floor:
    rng = SeededRandom(seed)
    budget = floor_budget(floor_index)
    base = budget // R.ENEMY_ROOMS_PER_FLOOR
    rooms = [
        Room(type=RoomType.ENEMY, data={"difficulty": max(1, base + rng.randint(-base // 4, base // 4))})
        for _ in range(R.ENEMY_ROOMS_PER_FLOOR)
    ]
    rooms.append(Room(type=choose_special(floor_index, rng)))
    adjacency = [[i + 1] for i in range(len(rooms) - 1)] + [[]]
    return Floor(seed=seed, floor_index=floor_index, rooms=rooms, adjacency=adjacency)


def floor_difficulty(floor: Floor) -> int:
    return sum(r.data.get("difficulty", 0) for r in floor.rooms if r.type == RoomType.ENEMY)


def in_band(floor: Floor) -> bool:
    budget = floor_budget(floor.floor_index)
    diff = floor_difficulty(floor)
    return abs(diff - budget) <= budget * 0.25


def reachable(floor: Floor) -> bool:
    n = len(floor.rooms)
    seen = {0}
    stack = [0]
    while stack:
        node = stack.pop()
        for nxt in floor.adjacency[node]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return len(seen) == n

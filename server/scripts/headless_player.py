"""Headless engine driver (T2.5) — walks a sector, fights via the sim, validates invariants.

No LLM, no network: exercises floorgen + rules + sim core + catalog directly.
"""

from __future__ import annotations

import argparse
import sys

from app.game import floorgen, rules as R
from app.game.catalog import get_class, load
from app.game.models import Player, RoomType
from app.game.sim import core


def make_player(class_id: str) -> Player:
    cls = get_class(class_id)
    stats = cls["stats"]
    p = Player(
        hp=stats["max_hp"], max_hp=stats["max_hp"],
        attack=stats["attack"], defense=stats["defense"],
        class_tag=cls["class_tag"],
    )
    p.recompute_build_tags()
    return p


def fight(player: Player, enemy: dict, seed: int) -> Player:
    state = core.new_fight(
        seed=seed, player_atk=player.attack, player_def=player.defense,
        enemy_hp=enemy["max_hp"], enemy_atk=enemy["attack"], enemy_def=enemy["defense"],
        enemy_posture=enemy["posture"],
    )
    for _ in range(R.FIGHT_TICK_LIMIT):
        dist = state["ex"] - state["px"]
        if abs(dist) > core.ATTACK_RANGE:
            move = (500 if dist > 0 else -500, 0)
            action = "none"
        elif state["ecooldown"] <= 2 and state["pstate"] == core.IDLE and state["pstam"] >= core.STAMINA_ROLL:
            move = (0, 0)
            action = "roll"
        else:
            move = (0, 0)
            action = "attack" if state["pstate"] == core.IDLE and state["pstam"] >= core.STAMINA_ATTACK else "none"
        state, _ = core.step(state, move, action)
        if state["ehp"] <= 0:
            player.hp = max(0, state["php"])
            return player
        if state["php"] <= 0:
            player.hp = 0
            return player
    player.hp = max(0, state["php"])
    return player


def run_sector(class_id: str, sector: int, seed: int) -> tuple[Player, list[str]]:
    player = make_player(class_id)
    events: list[str] = []
    boss = next(b for b in load()["bosses"] if b["floor"] == sector * R.FLOORS_PER_SECTOR)
    for pos in range(1, R.FLOORS_PER_SECTOR + 1):
        floor_index = (sector - 1) * R.FLOORS_PER_SECTOR + pos
        floor = floorgen.generate_floor(seed=seed + floor_index, floor_index=floor_index)
        assert len(floor.rooms) == R.ROOMS_PER_FLOOR, "4-room invariant broken"
        for room in floor.rooms:
            if room.type == RoomType.ENEMY:
                diff = room.data["difficulty"]
                enemy = {"max_hp": diff, "attack": 4 + diff // 20, "defense": 1 + diff // 50, "posture": 80}
                player = fight(player, enemy, seed=seed + floor_index + diff)
                if player.hp <= 0:
                    return player, events
            elif room.type == RoomType.SHRINE:
                events.append(f"floor {floor_index}: shrine reached")
            elif room.type == RoomType.BOSS:
                assert not R.can_descend(floor_index, boss_defeated=False), "boss floor must gate descent"
                budget = floorgen.floor_budget(floor_index)
                boss_stats = {
                    "max_hp": budget,
                    "attack": 8 + budget // 20,
                    "defense": budget // 20,
                    "posture": 120,
                }
                player = fight(player, boss_stats, seed=seed + floor_index)
                if player.hp <= 0:
                    return player, events
                events.append(f"floor {floor_index}: boss {boss['name']} defeated -> unlock {boss['skill_unlock']}")
    return player, events


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--class", dest="class_id", default="brawler")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sector", type=int, default=1)
    args = parser.parse_args(argv)

    player, events = run_sector(args.class_id, args.sector, args.seed)
    for e in events:
        print(f"  {e}")
    if player.hp <= 0:
        print(f"DEFEAT: {args.class_id} died on sector {args.sector}")
        return 1
    print(f"CLEARED sector {args.sector}: {args.class_id} hp={player.hp} tags={player.build_tags}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

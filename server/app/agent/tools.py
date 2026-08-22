"""Engine-gateway tools (T3.2) — the ONLY path the LLM uses to touch game state.

`commit_encounter` is the single write path into `Room.enemies[]` (wraps the
Wave-2 `place_enemy`). It is a synchronous critical section (zero awaits) and
requires an approved verifier verdict. Every tool validates args with Pydantic
`extra="forbid"` independent of any LLM output.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..game import floorgen
from ..game.models import Enemy, FightState, Floor, Player, Room, RoomType


class RuleViolation(Exception):
    pass


class EnemyVariant(BaseModel):
    model_config = {"extra": "forbid"}
    enemy_id: str
    name: str
    stats: dict[str, int]
    behavior_table: list[dict] = Field(default_factory=list)
    affixes: list[str] = Field(default_factory=list)


class CommitVerdict(BaseModel):
    model_config = {"extra": "forbid"}
    approved: bool
    source: Literal["judges", "fallback"]


class LoreFact(BaseModel):
    model_config = {"extra": "forbid"}
    fragment: str


class LoreStore:
    def __init__(self, max_calls: int = 3) -> None:
        self.max_calls = max_calls
        self.calls = 0
        self.facts: list[dict] = []

    def add(self, fragment: str) -> None:
        if self.calls >= self.max_calls:
            raise RuleViolation("lore call cap exceeded")
        self.facts.append({"fragment": fragment, "is_generated": True})
        self.calls += 1


def get_player_build(player: Player) -> dict:
    return {
        "class_tag": player.class_tag,
        "build_tags": player.build_tags,
        "attack": player.attack,
        "defense": player.defense,
        "max_hp": player.max_hp,
        "equipment": {
            "weapon": player.equipment.weapon.id if player.equipment.weapon else None,
            "armor": player.equipment.armor.id if player.equipment.armor else None,
            "accessory": player.equipment.accessory.id if player.equipment.accessory else None,
        },
    }


def get_floor_state(floor: Floor) -> dict:
    return {
        "floor_index": floor.floor_index,
        "rooms": [{"type": r.type.value, "enemy_count": len(r.enemies)} for r in floor.rooms],
    }


def get_fight_facts(fight: FightState) -> dict:
    return {"fight_id": fight.fight_id, "tick": fight.tick, "seed": fight.seed}


def compose_variant(build_tags: list[str], floor_tier: int) -> EnemyVariant:
    from ..game.catalog import load

    enemy = load()["enemies"][0]
    return EnemyVariant(
        enemy_id=enemy["id"], name=enemy["name"],
        stats=enemy["stats"], behavior_table=enemy["behavior_table"],
    )


def commit_encounter(floor: Floor, room: Room, variant: EnemyVariant, verdict: CommitVerdict) -> Enemy:
    if room.type != RoomType.ENEMY:
        raise RuleViolation("commit target is not an enemy room")
    if room.enemies:
        raise RuleViolation("room already has a committed encounter")
    if not verdict.approved:
        raise RuleViolation("commit requires an approved verifier verdict")
    enemy = Enemy(
        name=variant.name,
        parts=[variant.enemy_id],
        affixes=variant.affixes,
        stats=variant.stats,
        behavior_table=variant.behavior_table,
    )
    floorgen.place_enemy(room, enemy)
    return enemy


def save_lore_fact(store: LoreStore, fact: LoreFact) -> dict:
    store.add(fact.fragment)
    return {"fragment": fact.fragment, "is_generated": True}

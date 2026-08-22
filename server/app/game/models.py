"""Pydantic game-state models — the engine's source of truth (T2.1).

`build_tags` is derived from the class + equipped items, recomputed on
equip/unequip — never stored in graph state.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class GameModel(BaseModel):
    model_config = {"extra": "forbid"}


class RoomType(str, Enum):
    ENEMY = "enemy"
    LOOT = "loot"
    EVENT = "event"
    SHRINE = "shrine"
    MARKET = "market"
    BOSS = "boss"


class Item(GameModel):
    id: str
    name: str
    tags: list[str] = Field(default_factory=list)
    stat_profile: dict[str, int] = Field(default_factory=dict)


class Inventory(GameModel):
    items: list[Item] = Field(default_factory=list)


class Equipment(GameModel):
    weapon: Item | None = None
    armor: Item | None = None
    accessory: Item | None = None

    def all_tags(self) -> set[str]:
        tags: set[str] = set()
        for item in (self.weapon, self.armor, self.accessory):
            if item is not None:
                tags.update(item.tags)
        return tags


class Player(GameModel):
    hp: int
    max_hp: int
    attack: int
    defense: int
    level: int = 1
    xp: int = 0
    gold: int = 0
    class_tag: str
    equipment: Equipment = Field(default_factory=Equipment)
    build_tags: list[str] = Field(default_factory=list)

    def recompute_build_tags(self) -> None:
        tags = {self.class_tag}
        tags.update(self.equipment.all_tags())
        self.build_tags = sorted(tags)

    def equip(self, item: Item, slot: str) -> None:
        setattr(self.equipment, slot, item)
        self.recompute_build_tags()

    def unequip(self, slot: str) -> None:
        setattr(self.equipment, slot, None)
        self.recompute_build_tags()


class Enemy(GameModel):
    name: str
    parts: list[str] = Field(default_factory=list)
    affixes: list[str] = Field(default_factory=list)
    stats: dict[str, int] = Field(default_factory=dict)
    behavior_table: list[dict] = Field(default_factory=list)


class Room(GameModel):
    type: RoomType
    enemies: list[Enemy] = Field(default_factory=list)
    data: dict = Field(default_factory=dict)


class Floor(GameModel):
    seed: int
    floor_index: int
    rooms: list[Room] = Field(default_factory=list)


class BossSkill(GameModel):
    id: str
    level: int = 1


class FightState(GameModel):
    fight_id: str
    seed: int
    tick: int = 0
    player_state: dict = Field(default_factory=dict)
    enemy_states: list[dict] = Field(default_factory=list)


class ShrineState(GameModel):
    lit: bool = False
    components_held: list[str] = Field(default_factory=list)


class MarketState(GameModel):
    stock: list[str] = Field(default_factory=list)
    restock_tick: int = 0


class HometownState(GameModel):
    banked_inventory: Inventory = Field(default_factory=Inventory)


class GameSession(GameModel):
    session_id: str
    resume_token: str
    seed: int
    player: Player
    current_floor: int = 1
    sector: int = 1
    anchor_floor: int = 1
    run_state: str = "hometown"
    terminal: bool = False
    learnt_boss_skills: list[BossSkill] = Field(default_factory=list)
    shrine: ShrineState = Field(default_factory=ShrineState)
    market: MarketState = Field(default_factory=MarketState)
    hometown: HometownState = Field(default_factory=HometownState)

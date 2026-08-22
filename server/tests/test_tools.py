"""T3.2 — engine-gateway tools: commit_encounter single write path, validation, provenance."""

import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.agent.tools import (
    CommitVerdict,
    EnemyVariant,
    LoreFact,
    LoreStore,
    RuleViolation,
    commit_encounter,
    compose_variant,
    get_floor_state,
    get_player_build,
    save_lore_fact,
)
from app.game.models import Floor, Player, Room, RoomType


def _player() -> Player:
    p = Player(hp=100, max_hp=100, attack=10, defense=5, class_tag="brawler")
    p.recompute_build_tags()
    return p


def _floor() -> Floor:
    rooms = [Room(type=RoomType.ENEMY) for _ in range(3)]
    rooms.append(Room(type=RoomType.SHRINE))
    return Floor(seed=1, floor_index=3, rooms=rooms)


def _variant() -> EnemyVariant:
    return EnemyVariant(enemy_id="hound", name="Hound", stats={"max_hp": 40, "attack": 8, "defense": 2, "posture": 80})


def _verdict(approved: bool = True, source: str = "judges") -> CommitVerdict:
    return CommitVerdict(approved=approved, source=source)


def test_tools_callable():
    assert "brawler" in get_player_build(_player())["build_tags"]
    state = get_floor_state(_floor())
    assert state["floor_index"] == 3 and len(state["rooms"]) == 4
    assert compose_variant(["brawler"], 1).enemy_id


def test_invalid_args_rejected():
    with pytest.raises(ValidationError):
        EnemyVariant(enemy_id="x", name="X", stats={}, invented=42)
    with pytest.raises(ValidationError):
        CommitVerdict(approved=True, source="invented")


def test_commit_encounter_appends_enemy():
    floor = _floor()
    room = floor.rooms[0]
    enemy = commit_encounter(floor, room, _variant(), _verdict())
    assert len(room.enemies) == 1
    assert enemy.name == "Hound"


def test_commit_encounter_rejects_non_enemy_room():
    floor = _floor()
    shrine = floor.rooms[3]  # RoomType.SHRINE
    with pytest.raises(RuleViolation):
        commit_encounter(floor, shrine, _variant(), _verdict())


def test_commit_encounter_rejects_already_populated():
    floor = _floor()
    room = floor.rooms[0]
    commit_encounter(floor, room, _variant(), _verdict())
    with pytest.raises(RuleViolation):
        commit_encounter(floor, room, _variant(), _verdict())


def test_commit_encounter_requires_verdict():
    floor = _floor()
    with pytest.raises(RuleViolation):
        commit_encounter(floor, floor.rooms[0], _variant(), _verdict(approved=False))
    # fallback source is allowed (engine-standard content)
    commit_encounter(floor, floor.rooms[0], _variant(), _verdict(source="fallback"))


def test_commit_encounter_sole_append_path():
    game_dir = Path(__file__).resolve().parent.parent / "app" / "game"
    result = subprocess.run(["grep", "-rn", ".enemies.append", str(game_dir)], capture_output=True, text=True)
    hits = [l for l in result.stdout.splitlines() if l.strip()]
    assert len(hits) == 1 and "floorgen.py" in hits[0], f"enemies.append outside place_enemy: {hits}"


def test_provenance_forced():
    store = LoreStore()
    result = save_lore_fact(store, LoreFact(fragment="the beast has wings"))
    assert result["is_generated"] is True
    assert store.facts[0]["is_generated"] is True
    with pytest.raises(ValidationError):
        LoreFact(fragment="x", is_canonical=True)


def test_lore_call_cap():
    store = LoreStore(max_calls=3)
    for i in range(3):
        save_lore_fact(store, LoreFact(fragment=f"fact {i}"))
    assert store.calls == 3
    with pytest.raises(RuleViolation):
        save_lore_fact(store, LoreFact(fragment="fact 4"))

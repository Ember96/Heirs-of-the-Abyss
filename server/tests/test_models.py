"""T2.1 — Pydantic models, build-tag derivation, no module-level random."""

import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.game.models import Equipment, GameSession, Item, Player


def _player():
    return Player(hp=100, max_hp=100, attack=10, defense=5, class_tag="warrior")


def test_player_roundtrip():
    p = _player()
    p.recompute_build_tags()
    p2 = Player.model_validate(p.model_dump())
    assert p == p2


def test_build_tags_recomputed_on_equip_unequip():
    p = _player()
    p.recompute_build_tags()
    assert p.build_tags == ["warrior"]

    sword = Item(id="fire_sword", name="Fire Sword", tags=["fire", "sword"])
    p.equip(sword, "weapon")
    assert set(p.build_tags) == {"warrior", "fire", "sword"}

    p.unequip("weapon")
    assert p.build_tags == ["warrior"]


def test_missing_required_field_raises():
    with pytest.raises(ValidationError):
        Player(hp=100, max_hp=100, attack=10)


def test_extra_field_forbidden():
    with pytest.raises(ValidationError):
        Player(hp=1, max_hp=1, attack=1, defense=1, class_tag="x", invented=42)


def test_equipment_defaults_empty():
    assert Equipment().all_tags() == set()


def test_session_roundtrip():
    p = _player()
    p.recompute_build_tags()
    s = GameSession(session_id="s1", resume_token="rt", seed=42, player=p)
    s2 = GameSession.model_validate(s.model_dump())
    assert s == s2


def test_no_module_level_random():
    game_dir = Path(__file__).resolve().parent.parent / "app" / "game"
    result = subprocess.run(
        ["grep", "-rn", "-E", r"^import random|^from random|random\.", str(game_dir)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0, f"module-level random usage found:\n{result.stdout}"

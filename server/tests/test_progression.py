"""Progression loop (FR-3/FR-4) — descend/rest/return_home/shop via the WS server + unit tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import config
from app.game import progression
from app.game.catalog import get_class
from app.game.models import GameSession, Player
from app.main import app
from app.protocol import sign_frame


def _hello(ws, token: str = config.DEV_TOKEN) -> dict:
    ws.send_json({"v": 1, "type": "hello", "id": "h1", "seq": 0, "payload": {"token": token}})
    return ws.receive_json()


def _signed(ws, hk: str, type_: str, id_: str, seq: int, payload: dict) -> None:
    sig = sign_frame(bytes.fromhex(hk), type_, id_, seq, payload)
    ws.send_json({"v": 1, "type": type_, "id": id_, "seq": seq, "payload": payload, "hmac": sig})


def _session(gold: int = 100) -> GameSession:
    stats = get_class("brawler")["stats"]
    p = Player(
        hp=stats["max_hp"], max_hp=stats["max_hp"],
        attack=stats["attack"], defense=stats["defense"],
        class_tag="brawler", gold=gold,
    )
    return GameSession(session_id="s", resume_token="r", seed=42, player=p)


def test_descend_rest_return_home_shop_errors():
    with TestClient(app) as client:
        with client.websocket_connect("/game") as ws:
            hk = _hello(ws)["payload"]["hmac_key"]
            seq = 1

            # rest at floor 1 (shrine) -> heals + lights shrine
            _signed(ws, hk, "action", "a1", seq, {"action": "rest", "params": {}})
            r = ws.receive_json()
            assert r["type"] == "turn_result"
            assert r["payload"]["result"]["shrine_lit"] is True

            # descend -> floor 2
            seq += 1
            _signed(ws, hk, "action", "a2", seq, {"action": "descend", "params": {}})
            r = ws.receive_json()
            assert r["type"] == "turn_result"
            assert r["payload"]["result"]["floor_index"] == 2

            # rest at floor 2 (not shrine) -> rule_violation
            seq += 1
            _signed(ws, hk, "action", "a3", seq, {"action": "rest", "params": {}})
            r = ws.receive_json()
            assert r["type"] == "error"
            assert r["payload"]["code"] == "rule_violation"

            # shop without gold -> rule_violation
            seq += 1
            _signed(ws, hk, "action", "a4", seq, {"action": "shop", "params": {"item_id": "iron_sword"}})
            r = ws.receive_json()
            assert r["type"] == "error"
            assert r["payload"]["code"] == "rule_violation"

            # return_home
            seq += 1
            _signed(ws, hk, "action", "a5", seq, {"action": "return_home", "params": {}})
            r = ws.receive_json()
            assert r["type"] == "turn_result"
            assert r["payload"]["result"]["run_state"] == "hometown"


def test_shop_success_and_start_fight():
    s = _session(gold=100)
    r = progression.shop(s, "iron_sword")
    assert r["purchased"] == "iron_sword"
    assert s.player.gold == 80  # iron_sword price is 20
    assert len(s.hometown.banked_inventory.items) == 1

    s.current_floor = 2
    fight, spec = progression.start_fight(s, 0)
    assert spec["fight_id"] == fight.fight_id
    assert spec["opponent_spec"]["stats"]["max_hp"] > 0

    # room 3 is the special room (not ENEMY) -> error
    with pytest.raises(progression.ProgressionError):
        progression.start_fight(s, 3)


def test_apply_fight_result_rewards_win_only():
    s = _session(gold=0)
    assert progression.apply_fight_result(s, {"ehp": 0, "php": 100}) == {"gold": 20, "xp": 10}
    assert s.player.gold == 20
    # a loss grants nothing
    assert progression.apply_fight_result(s, {"ehp": 1, "php": 0}) == {}
    assert s.player.gold == 20


def test_boss_fight_unlocks_skill():
    s = _session()
    s.current_floor = 5
    s.sector = 1
    fight, spec = progression.start_fight(s, 3)  # room 3 on floor 5 is BOSS
    assert fight.is_boss is True
    assert spec["opponent_spec"]["is_boss"] is True
    rewards = progression.apply_fight_result(s, {"ehp": 0, "php": 100}, is_boss=True)
    assert rewards["skill_unlocked"] == "dash"
    assert any(sk.id == "dash" and sk.level == 1 for sk in s.learnt_boss_skills)
    # second unlock levels it up
    progression.apply_fight_result(s, {"ehp": 0, "php": 100}, is_boss=True)
    assert any(sk.id == "dash" and sk.level == 2 for sk in s.learnt_boss_skills)


def test_enter_room_returns_type():
    s = _session()
    s.current_floor = 2
    assert progression.enter_room(s, 0)["type"] == "enemy"
    assert progression.enter_room(s, 3)["type"] in ("loot", "event")

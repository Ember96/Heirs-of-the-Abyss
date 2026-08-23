"""End-to-end fight validation (FR-2) through the real WS server.

A scripted client fight is streamed as ``fight_input``; the server re-sims and
verifies. Correct result hash -> ``verified:true``; tampered hash -> ``verified:false``.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import config
from app.game.catalog import get_class
from app.game.fight import state_hash
from app.game.sim import core
from app.main import app
from app.protocol import sign_frame

_ATK = get_class("brawler")["stats"]["attack"]
_DEF = get_class("brawler")["stats"]["defense"]


def _hello(ws, token: str = config.DEV_TOKEN) -> dict:
    ws.send_json({"v": 1, "type": "hello", "id": "h1", "seq": 0, "payload": {"token": token}})
    return ws.receive_json()


def _signed(ws, hk: str, type_: str, id_: str, seq: int, payload: dict) -> None:
    sig = sign_frame(bytes.fromhex(hk), type_, id_, seq, payload)
    ws.send_json({"v": 1, "type": type_, "id": id_, "seq": seq, "payload": payload, "hmac": sig})


def _simulate(seed: int, opp: dict) -> tuple[list[tuple[int, str, tuple[int, int]]], dict]:
    state = core.new_fight(
        seed=seed, player_atk=_ATK, player_def=_DEF,
        enemy_hp=opp["max_hp"], enemy_atk=opp["attack"], enemy_def=opp["defense"],
        enemy_posture=opp["posture"],
    )
    log: list[tuple[int, str, tuple[int, int]]] = []
    for _ in range(3600):
        if state["php"] <= 0 or state["ehp"] <= 0:
            break
        dist = state["ex"] - state["px"]
        if abs(dist) > core.ATTACK_RANGE:
            move, action = (500 if dist > 0 else -500, 0), "none"
        elif state["pstate"] == core.IDLE and state["pstam"] >= core.STAMINA_ATTACK:
            move, action = (0, 0), "attack"
        else:
            move, action = (0, 0), "none"
        state, _ = core.step(state, move, action)
        log.append((state["tick"], action, move))
    return log, state


def test_fight_verified_true_then_tampered_false():
    with TestClient(app) as client:
        with client.websocket_connect("/game") as ws:
            hk = _hello(ws)["payload"]["hmac_key"]
            seq = 1
            _signed(ws, hk, "action", "a1", seq, {"action": "attack", "params": {"room_index": 0}})
            fb = ws.receive_json()
            assert fb["type"] == "fight_begin"
            fight_id = fb["id"]
            seed = fb["payload"]["seed"]
            opp = fb["payload"]["opponent_spec"]["stats"]

            log, state = _simulate(seed, opp)
            assert state["ehp"] <= 0, "scripted fight should win"

            for tick, action, move in log:
                seq += 1
                _signed(ws, hk, "fight_input", fight_id, seq,
                        {"fight_id": fight_id, "tick": tick, "action": action, "params": {"move": list(move)}})
                ack = ws.receive_json()
                assert ack["type"] == "fight_input_ack"

            # correct hash -> verified:true, with rewards
            seq += 1
            _signed(ws, hk, "fight_submit", fight_id, seq,
                    {"fight_id": fight_id, "claimed_result": {"php": state["php"], "ehp": state["ehp"]},
                     "state_hash": state_hash(state), "sim_version": "1"})
            fr = ws.receive_json()
            assert fr["type"] == "fight_result"
            assert fr["payload"]["verified"] is True
            assert fr["payload"]["rewards"]["gold"] == 20

            # tampered hash -> verified:false, no rewards
            seq += 1
            _signed(ws, hk, "fight_submit", fight_id, seq,
                    {"fight_id": fight_id, "claimed_result": {"php": 999, "ehp": 0},
                     "state_hash": "0" * 64, "sim_version": "1"})
            fr2 = ws.receive_json()
            assert fr2["type"] == "fight_result"
            assert fr2["payload"]["verified"] is False
            assert fr2["payload"]["rewards"] == {}

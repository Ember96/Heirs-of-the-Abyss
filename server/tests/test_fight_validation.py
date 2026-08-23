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


def _simulate(seed: int, opp: dict, behavior_table=None) -> tuple[list[tuple[int, str, tuple[int, int]]], dict]:
    state = core.new_fight(
        seed=seed, player_atk=_ATK, player_def=_DEF,
        enemy_hp=opp["max_hp"], enemy_atk=opp["attack"], enemy_def=opp["defense"],
        enemy_posture=opp["posture"], behavior_table=behavior_table or None,
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


def test_tampered_claim_counted_honest_win_stale_rejected(monkeypatch):
    from app.agent.tools import EnemyVariant
    from app.agent.verifiers import JudgeVerdict, VerifierVerdict
    from app.game.catalog import load

    enemy = load()["enemies"][0]
    variant = EnemyVariant(
        enemy_id=enemy["id"], name=enemy["name"],
        stats=dict(enemy["stats"]), behavior_table=enemy.get("behavior_table", []),
    )
    verdict = VerifierVerdict(approved=True, judges=[JudgeVerdict(judge="balance", passed=True)])
    monkeypatch.setattr("app.agent.director.compose_and_verify", lambda tags, tier: (variant, verdict))

    with TestClient(app) as client:
        with client.websocket_connect("/game") as ws:
            hk = _hello(ws)["payload"]["hmac_key"]
            seq = 1
            _signed(ws, hk, "action", "a1", seq, {"action": "attack", "params": {"room_index": 0}})
            fb = ws.receive_json()
            assert fb["type"] == "fight_begin"
            fight_id = fb["id"]
            seed = fb["payload"]["seed"]
            spec = fb["payload"]["opponent_spec"]

            log, state = _simulate(seed, spec["stats"], spec.get("behavior_table") or [])
            assert state["ehp"] <= 0, "scripted fight should win"

            for tick, action, move in log:
                seq += 1
                _signed(ws, hk, "fight_input", fight_id, seq,
                        {"fight_id": fight_id, "tick": tick, "action": action, "params": {"move": list(move)}})
                ack = ws.receive_json()
                assert ack["type"] == "fight_input_ack"

            # tampered claim while open -> verified:false, counted, no rewards
            seq += 1
            _signed(ws, hk, "fight_submit", fight_id, seq,
                    {"fight_id": fight_id, "claimed_result": {"php": 999, "ehp": 0},
                     "state_hash": "0" * 64, "sim_version": "1"})
            bad = ws.receive_json()
            assert bad["type"] == "fight_result"
            assert bad["payload"]["verified"] is False
            assert bad["payload"]["outcome"]["fail_count"] == 1
            assert bad["payload"]["rewards"] == {}

            # honest claim still wins inside the reject budget
            seq += 1
            _signed(ws, hk, "fight_submit", fight_id, seq,
                    {"fight_id": fight_id, "claimed_result": {"php": state["php"], "ehp": state["ehp"]},
                     "state_hash": state_hash(state), "sim_version": "1"})
            good = ws.receive_json()
            assert good["type"] == "fight_result"
            assert good["payload"]["verified"] is True
            assert good["payload"]["rewards"]["gold"] == 20

            # stale resubmit after resolution -> typed rejection
            seq += 1
            _signed(ws, hk, "fight_submit", fight_id, seq,
                    {"fight_id": fight_id, "claimed_result": {"php": state["php"], "ehp": 0},
                     "state_hash": state_hash(state), "sim_version": "1"})
            stale = ws.receive_json()
            assert stale["type"] == "error"
            assert stale["payload"]["code"] == "rule_violation"

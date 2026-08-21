"""T1.5 E2E socket conformance — proves the hardened WS path end-to-end."""

import time

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app
from app.protocol import sign_frame

DEV_TOKEN = config.DEV_TOKEN


def _hello(ws):
    ws.send_json({"v": 1, "type": "hello", "id": "h1", "seq": 0, "payload": {"token": DEV_TOKEN}})
    return ws.receive_json()


def _signed(hk, t, i, s, p):
    return {"v": 1, "type": t, "id": i, "seq": s, "payload": p,
            "hmac": sign_frame(bytes.fromhex(hk), t, i, s, p)}


def test_full_handshake_hmac():
    with TestClient(app) as c:
        with c.websocket_connect("/game") as ws:
            w = _hello(ws)
            assert w["type"] == "welcome"
            hk = w["payload"]["hmac_key"]
            ws.send_json(_signed(hk, "ping", "p1", 1, {}))
            p = ws.receive_json()
            assert p["type"] == "pong" and p["id"] == "p1"


def test_roundtrip_under_100ms():
    with TestClient(app) as c:
        with c.websocket_connect("/game") as ws:
            hk = _hello(ws)["payload"]["hmac_key"]
            t0 = time.perf_counter()
            ws.send_json(_signed(hk, "ping", "p1", 1, {}))
            ws.receive_json()
            ms = (time.perf_counter() - t0) * 1000
            assert ms < 100, f"round-trip {ms:.1f}ms exceeds 100ms"


def test_action_ordering():
    with TestClient(app) as c:
        with c.websocket_connect("/game") as ws:
            hk = _hello(ws)["payload"]["hmac_key"]
            ws.send_json(_signed(hk, "action", "a1", 1, {"action": "move", "params": {}}))
            ws.send_json(_signed(hk, "action", "a2", 2, {"action": "attack", "params": {}}))
            r1, r2 = ws.receive_json(), ws.receive_json()
            assert r1["type"] == "turn_result" and r1["id"] == "a1"
            assert r2["type"] == "turn_result" and r2["id"] == "a2"


def test_out_of_context_decision_rule_violation():
    with TestClient(app) as c:
        with c.websocket_connect("/game") as ws:
            hk = _hello(ws)["payload"]["hmac_key"]
            ws.send_json(_signed(hk, "decision", "d1", 1, {"decision_id": "d1", "option_id": "o1"}))
            e = ws.receive_json()
            assert e["type"] == "error" and e["payload"]["code"] == "rule_violation"


def test_stale_seq_closes():
    with TestClient(app) as c:
        with c.websocket_connect("/game") as ws:
            hk = _hello(ws)["payload"]["hmac_key"]
            ws.send_json(_signed(hk, "ping", "p1", 0, {}))
            with pytest.raises(Exception):
                ws.receive_json()


def test_resume_stub_returns_session_not_found():
    with TestClient(app) as c:
        with c.websocket_connect("/game") as ws:
            hk = _hello(ws)["payload"]["hmac_key"]
            ws.send_json(_signed(hk, "resume", "r1", 1, {"resume_token": "fake"}))
            e = ws.receive_json()
            assert e["type"] == "error"
            assert e["payload"]["code"] == "session_not_found"
            assert isinstance(e["payload"]["recoverable"], bool)


def test_generation_lifecycle_narrative_frames():
    with TestClient(app) as c:
        with c.websocket_connect("/game") as ws:
            hk = _hello(ws)["payload"]["hmac_key"]
            ws.send_json(_signed(hk, "action", "a1", 1, {"action": "talk", "params": {}}))
            d = ws.receive_json()
            e = ws.receive_json()
            assert d["type"] == "narrative_delta"
            assert e["type"] == "narrative_end"
            assert d["id"] == e["id"]


def test_generation_hang_sends_terminal_frame(monkeypatch):
    monkeypatch.setattr(config, "GENERATION_TIMEOUT", 0.1)
    with TestClient(app) as c:
        with c.websocket_connect("/game") as ws:
            hk = _hello(ws)["payload"]["hmac_key"]
            ws.send_json(_signed(hk, "action", "a1", 1, {"action": "_test_hang", "params": {}}))
            e = ws.receive_json()
            assert e["type"] == "error"
            assert e["payload"]["code"] == "generation_failed"
            assert e["payload"]["narrative_id"]


def test_busy_during_generation(monkeypatch):
    monkeypatch.setattr(config, "GENERATION_TIMEOUT", 5.0)
    with TestClient(app) as c:
        with c.websocket_connect("/game") as ws:
            hk = _hello(ws)["payload"]["hmac_key"]
            ws.send_json(_signed(hk, "action", "a1", 1, {"action": "_test_hang", "params": {}}))
            ws.send_json(_signed(hk, "decision", "d1", 2, {"decision_id": "d1", "option_id": "o1"}))
            e = ws.receive_json()
            assert e["type"] == "error"
            assert e["payload"]["code"] == "busy"


def test_100_pingpong_monotonic():
    with TestClient(app) as c:
        with c.websocket_connect("/game") as ws:
            hk = _hello(ws)["payload"]["hmac_key"]
            last = -1
            for i in range(1, 101):
                ws.send_json(_signed(hk, "ping", f"p{i}", i, {}))
                p = ws.receive_json()
                assert p["type"] == "pong"
                assert p["id"] == f"p{i}"
                assert p["seq"] > last
                last = p["seq"]


def test_oversized_frame_rejected_connection_open():
    with TestClient(app) as c:
        with c.websocket_connect("/game") as ws:
            hk = _hello(ws)["payload"]["hmac_key"]
            big = {"action": "move", "params": {"data": "x" * (70 * 1024)}}
            ws.send_json(_signed(hk, "action", "a1", 1, big))
            e = ws.receive_json()
            assert e["type"] == "error" and e["payload"]["code"] == "frame_too_large"
            ws.send_json(_signed(hk, "ping", "p2", 2, {}))
            assert ws.receive_json()["type"] == "pong"


def test_server_seq_monotonic():
    with TestClient(app) as c:
        with c.websocket_connect("/game") as ws:
            w = _hello(ws)
            assert w["seq"] == 0
            hk = w["payload"]["hmac_key"]
            last = w["seq"]
            ws.send_json(_signed(hk, "action", "a1", 1, {"action": "talk", "params": {}}))
            d = ws.receive_json()
            assert d["seq"] > last
            last = d["seq"]
            e = ws.receive_json()
            assert e["seq"] > last

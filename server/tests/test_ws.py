"""T1.3 conformance: hardened WS gateway (auth, HMAC, seq, ping/pong, generation tracker)."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app
from app.protocol import sign_frame
from app.ws import GenerationTracker, TokenBucket


def _hello(ws, token: str) -> dict:
    ws.send_json({"v": 1, "type": "hello", "id": "h1", "seq": 0, "payload": {"token": token}})
    return ws.receive_json()


def _signed(ws, hmac_key_hex: str, type_: str, id_: str, seq: int, payload: dict) -> None:
    sig = sign_frame(bytes.fromhex(hmac_key_hex), type_, id_, seq, payload)
    ws.send_json({"v": 1, "type": type_, "id": id_, "seq": seq, "payload": payload, "hmac": sig})


def test_health():
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


def test_handshake_and_pingpong():
    with TestClient(app) as client:
        with client.websocket_connect("/game") as ws:
            welcome = _hello(ws, config.DEV_TOKEN)
            assert welcome["type"] == "welcome"
            assert welcome["payload"]["session_id"] == welcome["id"]
            hmac_key = welcome["payload"]["hmac_key"]
            assert len(bytes.fromhex(hmac_key)) == 32
            assert welcome["payload"]["resume_token"]

            _signed(ws, hmac_key, "ping", "p1", 1, {})
            pong = ws.receive_json()
            assert pong["type"] == "pong"
            assert pong["id"] == "p1"


def test_bad_token_rejected():
    with TestClient(app) as client:
        with client.websocket_connect("/game") as ws:
            err = _hello(ws, "wrong-token")
            assert err["type"] == "error"
            assert err["payload"]["code"] == "auth_failed"


def test_non_hello_first_rejected():
    with TestClient(app) as client:
        with client.websocket_connect("/game") as ws:
            ws.send_json({"v": 1, "type": "ping", "id": "p1", "seq": 0, "payload": {}})
            err = ws.receive_json()
            assert err["type"] == "error"
            assert err["payload"]["code"] == "auth_failed"


def test_bad_hmac_rejected_connection_stays_open():
    with TestClient(app) as client:
        with client.websocket_connect("/game") as ws:
            welcome = _hello(ws, config.DEV_TOKEN)
            hmac_key = welcome["payload"]["hmac_key"]

            # tampered payload → signature mismatch
            sig = sign_frame(bytes.fromhex(hmac_key), "ping", "p1", 1, {"tampered": True})
            ws.send_json({"v": 1, "type": "ping", "id": "p1", "seq": 1, "payload": {}, "hmac": sig})
            err = ws.receive_json()
            assert err["type"] == "error"
            assert err["payload"]["code"] == "hmac_invalid"

            # connection still open: a correctly-signed ping now succeeds
            _signed(ws, hmac_key, "ping", "p2", 2, {})
            pong = ws.receive_json()
            assert pong["type"] == "pong"


@pytest.mark.asyncio
async def test_generation_force_cleared_on_timeout():
    timeouts = []

    async def on_timeout(nid):
        timeouts.append(nid)

    tracker = GenerationTracker(timeout=0.05, on_timeout=on_timeout)
    tracker.start("n1", asyncio.sleep(5.0))
    assert "n1" in tracker.in_flight
    await asyncio.sleep(0.15)
    assert "n1" not in tracker.in_flight
    assert timeouts == ["n1"]


@pytest.mark.asyncio
async def test_generation_completes_cleanly():
    timeouts = []

    async def on_timeout(nid):
        timeouts.append(nid)

    tracker = GenerationTracker(timeout=1.0, on_timeout=on_timeout)
    await tracker.start("n2", asyncio.sleep(0.01))
    assert "n2" not in tracker.in_flight
    assert timeouts == []


def test_token_bucket_limits():
    tb = TokenBucket(rate=0.0, capacity=3)
    assert all(tb.allow() for _ in range(3))
    assert not tb.allow()

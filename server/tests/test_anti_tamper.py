"""T6.3 — anti-tamper: fuzz malformed/replayed/forged frames (typed errors, no crash)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app import config
from app.main import app
from app.protocol import ERROR_CODES, MAX_FRAME_BYTES, RESUME_TOKEN_BYTES, sign_frame


def _hello(ws, token: str = config.DEV_TOKEN) -> dict:
    ws.send_json({"v": 1, "type": "hello", "id": "h1", "seq": 0, "payload": {"token": token}})
    return ws.receive_json()


def _drain(ws) -> tuple[list[str], int | None]:
    """Receive until close; return (error_codes_seen, close_code)."""
    codes: list[str] = []
    close_code: int | None = None
    try:
        while True:
            frame = ws.receive_json()
            if frame["type"] == "error":
                codes.append(frame["payload"]["code"])
    except WebSocketDisconnect as exc:
        close_code = exc.code
    return codes, close_code


# ── fatal frames: server closes cleanly (1007/1008), never crashes ──────────
FATAL_FRAMES = [
    "not json at all",
    "[]",
    '"just a string"',
    "42",
    '{"type": "ping", "id": "x", "seq": 0, "payload": {}}',           # missing v
    '{"v": 1, "type": "bogus", "id": "x", "seq": 0, "payload": {}}',   # unknown type
    '{"v": 1, "type": "ping", "id": "", "seq": 0, "payload": {}}',     # empty id
    '{"v": 1, "type": "ping", "id": "x", "seq": -1, "payload": {}}',   # negative seq
    '{"v": 1, "type": "ping", "id": "x", "seq": 0, "payload": "nope"}',  # payload not dict
]


@pytest.mark.parametrize("raw", FATAL_FRAMES)
def test_malformed_frame_closes_cleanly(raw: str):
    with TestClient(app) as client:
        with client.websocket_connect("/game") as ws:
            ws.send_text(raw)
            codes, close_code = _drain(ws)
            assert close_code in (1007, 1008)
            assert all(c in ERROR_CODES for c in codes)


def test_oversized_frame_rejected_with_typed_error():
    with TestClient(app) as client:
        with client.websocket_connect("/game") as ws:
            ws.send_text("x" * (MAX_FRAME_BYTES + 1))
            frame = ws.receive_json()
            assert frame["type"] == "error"
            assert frame["payload"]["code"] == "frame_too_large"


def test_seq_replay_closes_connection():
    with TestClient(app) as client:
        with client.websocket_connect("/game") as ws:
            welcome = _hello(ws)
            hmac_key = welcome["payload"]["hmac_key"]
            sig = sign_frame(bytes.fromhex(hmac_key), "ping", "p1", 1, {})
            ws.send_json({"v": 1, "type": "ping", "id": "p1", "seq": 1, "payload": {}, "hmac": sig})
            assert ws.receive_json()["type"] == "pong"
            # replay the same seq → anti-replay close
            ws.send_json({"v": 1, "type": "ping", "id": "p2", "seq": 1, "payload": {}, "hmac": sig})
            codes, close_code = _drain(ws)
            assert close_code == 1008
            assert codes == []


def test_forged_resume_token_rejected():
    with TestClient(app) as client:
        with client.websocket_connect("/game") as ws:
            welcome = _hello(ws)
            hmac_key = welcome["payload"]["hmac_key"]
            sig = sign_frame(bytes.fromhex(hmac_key), "resume", "r1", 1, {"resume_token": "forged-token"})
            ws.send_json({"v": 1, "type": "resume", "id": "r1", "seq": 1, "payload": {"resume_token": "forged-token"}, "hmac": sig})
            frame = ws.receive_json()
            assert frame["type"] == "error"
            assert frame["payload"]["code"] == "session_not_found"


def test_resume_token_high_entropy():
    import secrets

    tokens = {secrets.token_urlsafe(RESUME_TOKEN_BYTES) for _ in range(100)}
    assert len(tokens) == 100  # all distinct -> no guessable/trivial token
    assert all(len(t) >= 40 for t in tokens)  # 32 bytes -> ~43 url-safe chars

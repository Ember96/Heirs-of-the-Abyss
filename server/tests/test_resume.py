"""T3.5 — WS resume flow: hello persists a session, resume restores it."""

import json

import pytest

from app.game.models import GameSession, Player
from app.persistence import SessionStore
from app.ws import Connection


class FakeWS:
    def __init__(self):
        self.sent: list[str] = []

    async def send_text(self, text: str):
        self.sent.append(text)

    async def accept(self):
        pass

    async def close(self, code=1000):
        pass


def _session(sid="s1", token="rt1"):
    p = Player(hp=100, max_hp=100, attack=10, defense=5, class_tag="brawler")
    p.recompute_build_tags()
    return GameSession(session_id=sid, resume_token=token, seed=42, player=p)


@pytest.mark.asyncio
async def test_resume_sends_state_sync(tmp_path):
    store = SessionStore(tmp_path / "s.db")
    await store.create(_session("s1", "rt1"))

    conn = Connection(FakeWS(), store=store, signing_enabled=False)
    conn.authenticated = True
    await conn._handle_resume({"resume_token": "rt1"})

    frames = [json.loads(s) for s in conn.ws.sent]
    assert frames[0]["type"] == "state_sync"
    assert frames[0]["payload"]["state"]["session_id"] == "s1"
    assert conn.session_id == "s1"


@pytest.mark.asyncio
async def test_resume_unknown_token(tmp_path):
    store = SessionStore(tmp_path / "s.db")
    conn = Connection(FakeWS(), store=store, signing_enabled=False)
    conn.authenticated = True
    await conn._handle_resume({"resume_token": "nope"})

    frames = [json.loads(s) for s in conn.ws.sent]
    assert frames[0]["type"] == "error"
    assert frames[0]["payload"]["code"] == "session_not_found"


@pytest.mark.asyncio
async def test_hello_persists_session(tmp_path):
    store = SessionStore(tmp_path / "s.db")
    conn = Connection(FakeWS(), store=store, signing_enabled=False, dev_token="tok")
    await conn._handle_hello("h1", {"token": "tok"})

    session = await store.get_by_resume_token(conn.resume_token)
    assert session is not None
    assert session.session_id == conn.session_id

"""FR-7.3 / T3.1 — resume order (narrative_replay after state_sync) + talk->busy during generation."""

from __future__ import annotations

import json

import pytest

from app.game.models import GameSession, Player
from app.persistence import SessionStore
from app.ws import Connection, _mark_narration


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


def _frames(conn) -> list[dict]:
    return [json.loads(s) for s in conn.ws.sent]


@pytest.mark.asyncio
async def test_talk_during_generation_busy():
    async def hang():
        import asyncio
        await asyncio.Event().wait()

    conn = Connection(FakeWS(), signing_enabled=False)
    conn.authenticated = True
    conn.session_id = "sx"
    conn.start_generation("n-hang", hang())
    await conn._handle_action("a1", {"action": "talk", "params": {"text": "hello"}})
    frames = _frames(conn)
    assert frames[0]["type"] == "error"
    assert frames[0]["payload"]["code"] == "busy"


@pytest.mark.asyncio
async def test_resume_replays_cut_narrative(tmp_path):
    store = SessionStore(tmp_path / "s.db")
    await store.create(_session("s1", "rt1"))
    _mark_narration("s1", complete=False)  # stream was cut mid-generation

    conn = Connection(FakeWS(), store=store, signing_enabled=False)
    conn.authenticated = True
    await conn._handle_resume({"resume_token": "rt1"})

    frames = _frames(conn)
    assert [f["type"] for f in frames] == ["state_sync", "narrative_replay"]
    assert frames[1]["payload"]["offset"] == 0


@pytest.mark.asyncio
async def test_resume_skips_completed_narrative(tmp_path):
    store = SessionStore(tmp_path / "s.db")
    await store.create(_session("s2", "rt2"))
    _mark_narration("s2", complete=True)  # stream finished cleanly

    conn = Connection(FakeWS(), store=store, signing_enabled=False)
    conn.authenticated = True
    await conn._handle_resume({"resume_token": "rt2"})

    assert [f["type"] for f in _frames(conn)] == ["state_sync"]

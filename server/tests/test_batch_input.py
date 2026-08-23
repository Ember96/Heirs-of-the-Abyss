"""T7.7 — batched fight_input: one ack per frame, idempotent ticks, malformed rejection."""

from __future__ import annotations

import json

import pytest

from app.game.fight import FightSession
from app.game.models import GameSession, Player
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


def _frames(conn) -> list[dict]:
    return [json.loads(s) for s in conn.ws.sent]


def _conn() -> Connection:
    p = Player(hp=100, max_hp=100, attack=50, defense=20, class_tag="brawler")
    p.recompute_build_tags()
    sess = GameSession(session_id="sb", resume_token="rt", seed=9, player=p)
    conn = Connection(FakeWS(), signing_enabled=False)
    conn.authenticated = True
    conn.session_id = sess.session_id
    conn._session = sess
    conn._fights["f-b"] = FightSession(
        fight_id="f-b", seed=5, player_atk=50, player_def=20,
        enemy_hp=99999, enemy_atk=1, enemy_def=0, enemy_posture=999, enemy_x=0,
    )
    return conn


@pytest.mark.asyncio
async def test_batch_of_60_ticks_yields_one_ack():
    conn = _conn()
    batch = [{"tick": t, "action": "none", "params": {"move": [0, 0]}} for t in range(1, 61)]
    await conn._handle_fight_input("i", {"fight_id": "f-b", "batch": batch})

    frames = _frames(conn)
    assert len(frames) == 1
    assert frames[0]["type"] == "fight_input_ack"
    assert frames[0]["payload"]["last_tick"] == 60
    assert conn._fights["f-b"].last_tick == 60


@pytest.mark.asyncio
async def test_stale_and_duplicate_ticks_are_idempotent():
    conn = _conn()

    async def send(ticks):
        batch = [{"tick": t, "action": "none", "params": {"move": [0, 0]}} for t in ticks]
        await conn._handle_fight_input("i", {"fight_id": "f-b", "batch": batch})

    await send(range(1, 11))
    await send(range(5, 16))  # overlaps 5..10, extends to 15
    ack = _frames(conn)[-1]
    assert ack["payload"]["last_tick"] == 15
    assert conn._fights["f-b"].last_tick == 15


@pytest.mark.asyncio
async def test_malformed_batch_rejected_frame_invalid():
    conn = _conn()
    before = conn._fights["f-b"].last_tick
    await conn._handle_fight_input("i", {
        "fight_id": "f-b",
        "batch": [{"tick": 1}, {"tick": 2, "action": "none"}],  # first item missing action
    })
    frame = _frames(conn)[-1]
    assert frame["type"] == "error"
    assert frame["payload"]["code"] == "frame_invalid"
    assert conn._fights["f-b"].last_tick == before

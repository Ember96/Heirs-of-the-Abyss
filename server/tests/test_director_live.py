"""T7.5 — live director over WS: talk through the graph; encounters composed, gated, committed."""

from __future__ import annotations

import json

import pytest

from app.agent import director
from app.agent.tools import EnemyVariant
from app.agent.verifiers import JudgeVerdict, VerifierVerdict
from app.game.catalog import load
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


def _session(class_tag="brawler", sid="s1") -> GameSession:
    stats = {"brawler": (100, 12, 10), "alchemist": (90, 8, 6)}[class_tag]
    p = Player(hp=stats[0], max_hp=stats[0], attack=stats[1], defense=stats[2], class_tag=class_tag)
    p.recompute_build_tags()
    return GameSession(session_id=sid, resume_token="rt", seed=42, player=p)


def _conn(session: GameSession) -> Connection:
    conn = Connection(FakeWS(), signing_enabled=False)
    conn.authenticated = True
    conn.session_id = session.session_id
    conn._session = session
    return conn


@pytest.mark.asyncio
async def test_talk_routes_through_graph(monkeypatch):
    import asyncio

    seen = {}

    def fake_narrate(floor_index, player_text, build_tags):
        seen.update(floor=floor_index, text=player_text, tags=list(build_tags))
        return "Grim."

    monkeypatch.setattr(director, "narrate", fake_narrate)
    sess = _session()
    sess.current_floor = 3
    conn = _conn(sess)

    await conn._handle_action("a1", {"action": "talk", "params": {"text": "I look around"}})
    tasks = list(conn._generations._in_flight.values())
    await asyncio.gather(*tasks)

    frames = _frames(conn)
    assert [f["type"] for f in frames] == ["narrative_delta", "narrative_end"]
    assert frames[0]["payload"]["text"] == "Grim."
    assert seen == {"floor": 3, "text": "I look around", "tags": ["brawler"]}
    assert conn._parked is None


@pytest.mark.asyncio
async def test_two_builds_probe_different_compositions(monkeypatch):
    captured = []
    variant = EnemyVariant(enemy_id="hound", name="Hound", stats={"max_hp": 40, "attack": 8, "defense": 2})

    def fake_compose(tags, tier):
        captured.append(list(tags))
        verdict = VerifierVerdict(approved=True, judges=[JudgeVerdict(judge="rules", passed=True)])
        return variant, verdict

    monkeypatch.setattr(director, "compose_and_verify", fake_compose)

    for tag, sid in (("brawler", "sb"), ("alchemist", "sa")):
        sess = _session(class_tag=tag, sid=sid)
        sess.current_floor = 2
        conn = _conn(sess)
        await conn._handle_action("atk", {"action": "attack", "params": {"room_index": 0}})
        fb = _frames(conn)[-1]
        assert fb["type"] == "fight_begin"

    assert captured == [["brawler"], ["alchemist"]]


@pytest.mark.asyncio
async def test_committed_variant_feeds_the_fight(monkeypatch):
    variant = EnemyVariant(
        enemy_id="gargoyle", name="Gargoyle",
        stats={"max_hp": 123, "attack": 9, "defense": 3, "posture": 80},
    )
    verdict = VerifierVerdict(approved=True, judges=[JudgeVerdict(judge="balance", passed=True)])
    monkeypatch.setattr(director, "compose_and_verify", lambda t, r: (variant, verdict))

    sess = _session()
    sess.current_floor = 2
    conn = _conn(sess)
    await conn._handle_action("atk", {"action": "attack", "params": {"room_index": 0}})

    fb = _frames(conn)[-1]
    assert fb["type"] == "fight_begin"
    assert fb["payload"]["opponent_spec"]["stats"]["max_hp"] == 123
    assert fb["payload"]["opponent_spec"]["composed"] is True
    assert "f-" in fb["id"]


@pytest.mark.asyncio
async def test_judges_reject_parks_decision_then_fallback(monkeypatch):
    def failing_compose(tags, tier):
        raise ValueError("clamp exploded")

    monkeypatch.setattr(director, "compose_and_verify", failing_compose)
    sess = _session()
    sess.current_floor = 2
    conn = _conn(sess)

    await conn._handle_action("atk", {"action": "attack", "params": {"room_index": 0}})
    req = _frames(conn)[-1]
    assert req["type"] == "decision_request"
    assert req["payload"]["options"][0]["option_id"] == "fallback"
    assert conn._parked is not None

    await conn._resume_parked({"decision_id": req["id"], "option_id": "fallback"})

    fb = _frames(conn)[-1]
    assert fb["type"] == "fight_begin"
    assert "composed" not in fb["payload"]["opponent_spec"]
    assert conn._parked is None


@pytest.mark.asyncio
async def test_flee_option_ends_without_a_fight(monkeypatch):
    def always_fails(tags, tier):
        raise ValueError("x")

    monkeypatch.setattr(director, "compose_and_verify", always_fails)
    sess = _session()
    sess.current_floor = 2
    conn = _conn(sess)

    await conn._handle_action("atk", {"action": "attack", "params": {"room_index": 0}})
    req = _frames(conn)[-1]
    assert req["type"] == "decision_request"

    await conn._resume_parked({"decision_id": req["id"], "option_id": "flee"})
    last = _frames(conn)[-1]
    assert last["type"] == "turn_result"
    assert last["payload"]["result"]["fled"] is True

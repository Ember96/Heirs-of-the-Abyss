"""T7.5 — agent graph: live routing, committed encounters, interrupt/resume determinism."""

from __future__ import annotations

import pytest
from langgraph.types import Command

from app.agent import director
from app.agent.graph import OPTION_FALLBACK, OPTION_FLEE, build_graph
from app.agent.tools import EnemyVariant
from app.agent.verifiers import JudgeVerdict, VerifierVerdict
from app.game.catalog import load


def _approved_variant() -> EnemyVariant:
    enemy = load()["enemies"][0]
    return EnemyVariant(
        enemy_id=enemy["id"],
        name=enemy["name"],
        stats=dict(enemy["stats"]),
        behavior_table=enemy["behavior_table"],
    )


def _encounter_state(seed=99, floor_index=2, room_index=0) -> dict:
    return {
        "intent": "encounter_gen",
        "session_id": "s",
        "seed": seed,
        "floor_index": floor_index,
        "room_index": room_index,
        "tier": 1,
        "build_tags": ["brawler"],
    }


def _failing_compose(tags, tier):
    raise ValueError("clamp exploded")


def test_graph_compiles():
    assert build_graph() is not None


async def test_narrate_streams_and_terminates(monkeypatch):
    monkeypatch.setattr(director, "narrate", lambda *a: "Grim prose.")
    graph = build_graph()
    config = {"configurable": {"thread_id": "t-nar"}}
    result = await graph.ainvoke({"intent": "narrate", "session_id": "s"}, config)
    assert result["narrative"] == "Grim prose."
    assert result["route"] == "narrate"
    snapshot = await graph.aget_state(config)
    assert snapshot.next == ()


async def test_unknown_intent_falls_back_to_narrate(monkeypatch):
    monkeypatch.setattr(director, "narrate", lambda *a: "x")
    graph = build_graph()
    config = {"configurable": {"thread_id": "t-fb"}}
    result = await graph.ainvoke({"intent": "sing_a_song", "session_id": "s"}, config)
    assert result["route"] == "narrate"


async def test_approved_commit_reaches_room_without_parking(monkeypatch):
    seen = {}
    variant = _approved_variant()

    def fake_compose(tags, tier):
        seen["tags"] = list(tags)
        return variant, VerifierVerdict(approved=True, judges=[JudgeVerdict(judge="balance", passed=True)])

    monkeypatch.setattr(director, "compose_and_verify", fake_compose)
    graph = build_graph()
    config = {"configurable": {"thread_id": "t-commit"}}
    result = await graph.ainvoke(_encounter_state(), config)

    assert seen["tags"] == ["brawler"]
    assert result["committed"] is True
    assert result["variant"]["enemy_id"] == variant.enemy_id
    snapshot = await graph.aget_state(config)
    assert snapshot.next == ()


async def test_double_rejection_parks_then_fallback_resumes(monkeypatch):
    calls = {"n": 0}

    def counting_fail(tags, tier):
        calls["n"] += 1
        raise ValueError("clamp exploded")

    monkeypatch.setattr(director, "compose_and_verify", counting_fail)
    graph = build_graph()
    config = {"configurable": {"thread_id": "t-park"}}
    await graph.ainvoke(_encounter_state(), config)

    snapshot = await graph.aget_state(config)
    assert snapshot.next == ("wait_for_decision",)
    assert snapshot.values["pending_decision"]["options"][0]["option_id"] == OPTION_FALLBACK

    result = await graph.ainvoke(Command(resume=OPTION_FALLBACK), config)
    assert result["last_decision"] == OPTION_FALLBACK
    assert result["fallback"] is True
    assert calls["n"] == 2


async def test_flee_option_marks_withdrawal(monkeypatch):
    monkeypatch.setattr(director, "compose_and_verify", _failing_compose)
    graph = build_graph()
    config = {"configurable": {"thread_id": "t-flee"}}
    await graph.ainvoke(_encounter_state(), config)
    result = await graph.ainvoke(Command(resume=OPTION_FLEE), config)
    assert result["flee"] is True


async def test_checkpoint_persists_state(monkeypatch):
    monkeypatch.setattr(director, "narrate", lambda *a: "y")
    graph = build_graph()
    config = {"configurable": {"thread_id": "t-persist"}}
    await graph.ainvoke({"intent": "flavor", "session_id": "s42"}, config)
    snapshot = await graph.aget_state(config)
    assert snapshot.values["session_id"] == "s42"
    assert snapshot.values["route"] == "flavor"

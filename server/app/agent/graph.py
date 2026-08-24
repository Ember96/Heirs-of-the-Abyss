"""LangGraph dungeon-director (D4) — live orchestration for narration + encounters.

Engine-first routing: typed gameplay actions never enter this graph. Live routes
are ``narrate``/``flavor`` (LLM prose, terminal) and ``encounter_gen``
(compose -> clamp -> four judges -> ``commit_encounter``). If the judges reject
composition twice, the node parks the run at ``wait_for_decision`` (a real
LangGraph ``interrupt``) offering fallback-or-flee; the WS layer resumes it with
the player's ``Command(resume=...)``. Floor/boss composition rides the same
pipeline — room typing decides commit eligibility.
"""

from __future__ import annotations

import asyncio
from typing import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

ROUTES = ("encounter_gen", "narrate", "flavor")

OPTION_FALLBACK = "fallback"
OPTION_FLEE = "flee"
COMPOSE_ATTEMPTS = 2


class DirectorState(TypedDict, total=False):
    session_id: str
    current_floor: int
    intent: str
    route: str
    player_text: str
    build_tags: list
    seed: int
    floor_index: int
    room_index: int
    tier: int
    narrative: str
    variant: dict
    committed: bool
    fallback: bool
    flee: bool
    compose_attempts: int
    pending_decision: dict
    last_decision: str


def _route_intent(state: DirectorState) -> dict:
    intent = state.get("intent", "narrate")
    return {"route": intent if intent in ROUTES else "narrate"}


def _route_router(state: DirectorState) -> str:
    return state.get("route", "narrate")


async def _narrate_node(state: DirectorState) -> dict:
    from . import director

    text = await asyncio.to_thread(
        director.narrate,
        state.get("current_floor", 1),
        state.get("player_text", ""),
        list(state.get("build_tags", [])),
    )
    return {"narrative": text}


async def _flavor_node(state: DirectorState) -> dict:
    return await _narrate_node(state)


def _compose_and_commit(state: DirectorState) -> dict:
    from . import director
    from .tools import CommitVerdict, commit_encounter
    from ..game import floorgen

    floor = floorgen.generate_floor(
        seed=state["seed"] + state["floor_index"],
        floor_index=state["floor_index"],
    )
    room = floor.rooms[state["room_index"]]
    tags = list(state.get("build_tags", []))
    tier = state.get("tier", 1)

    last_error = ""
    for _ in range(COMPOSE_ATTEMPTS):
        try:
            variant, verdict = director.compose_and_verify(tags, tier)
            if not verdict.approved:
                last_error = "; ".join(j.reason for j in verdict.judges if not j.passed)
                continue
            gate = CommitVerdict(approved=True, source="judges")
            commit_encounter(floor, room, variant, gate)
            return {
                "variant": {**variant.model_dump(), "behavior_table": variant.behavior_table},
                "committed": True,
            }
        except Exception as exc:  # clamp/schema/LLM failures funnel to the repair gate
            last_error = str(exc)

    return {
        "pending_decision": {
            "prompt": f"The summoning rite fails ({last_error}). Face a lesser foe, or withdraw?",
            "options": [
                {"option_id": OPTION_FALLBACK, "label": "Face the lesser foe"},
                {"option_id": OPTION_FLEE, "label": "Withdraw"},
            ],
        },
        "compose_attempts": COMPOSE_ATTEMPTS,
    }


async def _encounter_gen_node(state: DirectorState) -> dict:
    return await asyncio.to_thread(_compose_and_commit, state)


def _wait_for_decision(state: DirectorState) -> dict:
    pending = state.get("pending_decision") or {}
    if not pending:
        return {}
    choice = interrupt(pending)
    return {"pending_decision": {}, "last_decision": str(choice)}


def _finalize_encounter(state: DirectorState) -> dict:
    updates: dict = {}
    decision = str(state.get("last_decision", ""))
    if decision == OPTION_FLEE or state.get("flee"):
        updates["flee"] = True
    elif decision == OPTION_FALLBACK or (not state.get("committed") and not decision):
        updates["fallback"] = True
    return updates


def build_graph(checkpointer=None):
    builder = StateGraph(DirectorState)
    builder.add_node("route_intent", _route_intent)
    builder.add_node("narrate", _narrate_node)
    builder.add_node("flavor", _flavor_node)
    builder.add_node("encounter_gen", _encounter_gen_node)
    builder.add_node("wait_for_decision", _wait_for_decision)
    builder.add_node("finalize_encounter", _finalize_encounter)
    builder.add_edge(START, "route_intent")
    builder.add_conditional_edges("route_intent", _route_router, list(ROUTES))
    builder.add_edge("narrate", END)
    builder.add_edge("flavor", END)
    builder.add_edge("encounter_gen", "wait_for_decision")
    builder.add_edge("wait_for_decision", "finalize_encounter")
    builder.add_edge("finalize_encounter", END)
    if checkpointer is None:
        checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)

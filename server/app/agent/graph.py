"""LangGraph dungeon-director (T3.1) — graph structure, interrupt, checkpointer.

Engine-first routing: typed gameplay actions (`move/attack/use_item/rest/…`)
NEVER enter this graph — the WS handler dispatches them straight to the engine.
Only free-form `talk`/flavor/decision intents run through the graph. State holds
session_id + floor + routing, never the player build (always fetched via tool).
"""

from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

ROUTES = ("floor_gen", "encounter_gen", "boss_gen", "narrate", "flavor")


class DirectorState(TypedDict, total=False):
    session_id: str
    current_floor: int
    intent: str
    route: str
    pending_decision: dict
    last_decision: str


def _route_intent(state: DirectorState) -> dict:
    intent = state.get("intent", "talk")
    return {"route": intent if intent in ROUTES else "narrate"}


def _route_router(state: DirectorState) -> str:
    return state.get("route", "narrate")


def _make_gen_node(name: str):
    def node(state: DirectorState) -> dict:
        return {
            "pending_decision": {
                "prompt": f"{name} stub — choose an option",
                "options": [{"option_id": "ok", "label": "Continue"}],
            }
        }

    return node


def _wait_for_decision(state: DirectorState) -> dict:
    decision = interrupt(state.get("pending_decision", {}))
    return {"pending_decision": {}, "last_decision": str(decision)}


def build_graph(checkpointer=None):
    builder = StateGraph(DirectorState)
    builder.add_node("route_intent", _route_intent)
    builder.add_node("floor_gen", _make_gen_node("floor_gen"))
    builder.add_node("encounter_gen", _make_gen_node("encounter_gen"))
    builder.add_node("boss_gen", _make_gen_node("boss_gen"))
    builder.add_node("narrate", _make_gen_node("narrate"))
    builder.add_node("flavor", _make_gen_node("flavor"))
    builder.add_node("wait_for_decision", _wait_for_decision)
    builder.add_edge(START, "route_intent")
    builder.add_conditional_edges("route_intent", _route_router, list(ROUTES))
    for route in ROUTES:
        builder.add_edge(route, "wait_for_decision")
    builder.add_edge("wait_for_decision", END)
    if checkpointer is None:
        checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)

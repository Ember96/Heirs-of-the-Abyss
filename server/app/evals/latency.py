"""Latency + cost measurement (T6.2)."""

from __future__ import annotations

import time

from ..game import rules as R
from ..game.sim import core

LATENCY_BUDGETS = {
    "turn_p50": 3.0,      # median gameplay turn (talk/flavor only; combat/explore are LLM-free)
    "turn_p95": 8.0,
    "ttft": 1.5,          # streaming time-to-first-token
    "ws_roundtrip": 0.1,  # echo round-trip (server -> client -> server)
    "re_sim": 1.0,        # full-fight re-simulation on reconnect resume
}


def measure_re_sim_time() -> float:
    """Re-simulate a worst-case full fight and return elapsed wall time (s)."""
    state = core.new_fight(seed=42)
    start = time.perf_counter()
    for _ in range(R.FIGHT_TICK_LIMIT):
        if state["pstate"] == core.IDLE and state["pstam"] >= core.STAMINA_ATTACK:
            action = "attack"
        else:
            action = "none"
        state, _ = core.step(state, (0, 0), action)
    return time.perf_counter() - start

"""Deterministic fight validation (FR-2) — the server re-sims the input log.

The client streams ``fight_input`` (tick, action, params.move); the server owns
the fight setup (seed + opponent stats) and re-sims the merged log on
``fight_submit`` to verify the claimed result hash. No client-trusted value:
a tampered result fails the hash check and grants no rewards.
"""

from __future__ import annotations

import hashlib

from .sim import core

SIM_VERSION = "1"


def state_hash(state: dict) -> str:
    """SHA-256 over the canonical sim-state JSON (matches the client mirror)."""
    return hashlib.sha256(core.canonical(state).encode("utf-8")).hexdigest()


class FightSession:
    """One fight: server-owned setup + idempotent input log + re-sim verification."""

    def __init__(
        self,
        fight_id: str,
        seed: int,
        player_atk: int,
        player_def: int,
        enemy_hp: int,
        enemy_atk: int,
        enemy_def: int,
        enemy_posture: int,
        enemy_x: int = 3000,
    ) -> None:
        self.fight_id = fight_id
        self.seed = seed
        self._setup = {
            "player_atk": player_atk,
            "player_def": player_def,
            "enemy_hp": enemy_hp,
            "enemy_atk": enemy_atk,
            "enemy_def": enemy_def,
            "enemy_posture": enemy_posture,
            "enemy_x": enemy_x,
        }
        self._log: dict[int, tuple[tuple[int, int], str]] = {}
        self._last_tick = 0

    def record_input(self, tick: int, action: str, move: list[int] | tuple[int, int]) -> int:
        """Append idempotently (dedupe by tick); return last_tick."""
        if tick > self._last_tick:
            m = (int(move[0]), int(move[1])) if move else (0, 0)
            self._log[tick] = (m, action)
            self._last_tick = tick
        return self._last_tick

    def _new_state(self) -> dict:
        return core.new_fight(seed=self.seed, **self._setup)

    def re_sim(self) -> dict:
        state = self._new_state()
        for tick in sorted(self._log):
            move, action = self._log[tick]
            state, _ = core.step(state, move, action)
        return state

    def verify(self, claimed_state_hash: str, sim_version: str) -> tuple[bool, dict]:
        if sim_version != SIM_VERSION:
            return False, {"reason": "sim_version_mismatch"}
        state = self.re_sim()
        verified = claimed_state_hash == state_hash(state)
        outcome = {"php": state["php"], "ehp": state["ehp"], "tick": state["tick"]}
        return verified, outcome

"""Deterministic fight validation (FR-2) — the server re-sims the input log.

The client streams ``fight_input`` (tick, action, params.move); the server owns
the fight setup (seed + opponent stats) and re-sims the merged log on
``fight_submit`` to verify the claimed result hash. No client-trusted value:
a tampered result fails the hash check and grants no rewards.

Lifecycle (FR-1.5 / FR-2.3 / FR-2.4): fights are serializable to/from the
session store so a crash or restart resumes the same log; ``verified:false``
failures accumulate in ``fail_count`` and at 2 the fight resolves as a flee;
past the tick limit the fight flees automatically. Fights end only in
``won`` / ``lost`` / ``fled`` states.
"""

from __future__ import annotations

import hashlib
import json

from . import rules as R
from .sim import core

SIM_VERSION = "1"
REJECT_LIMIT = 2


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
        is_boss: bool = False,
        behavior_table: list[dict] | None = None,
        fail_count: int = 0,
        status: str = "open",
    ) -> None:
        self.fight_id = fight_id
        self.seed = seed
        self.is_boss = is_boss
        self.fail_count = fail_count
        self.status = status
        self.setup = {
            "player_atk": player_atk,
            "player_def": player_def,
            "enemy_hp": enemy_hp,
            "enemy_atk": enemy_atk,
            "enemy_def": enemy_def,
            "enemy_posture": enemy_posture,
            "enemy_x": enemy_x,
            "behavior_table": behavior_table or [],
        }
        self._log: dict[int, tuple[tuple[int, int], str]] = {}
        self._last_tick = 0
        self.last_saved_tick = 0

    @property
    def last_tick(self) -> int:
        return self._last_tick

    @property
    def expired(self) -> bool:
        return self._last_tick >= R.FIGHT_TICK_LIMIT

    def record_input(self, tick: int, action: str, move: list[int] | tuple[int, int]) -> int:
        """Append idempotently (dedupe by tick); return last_tick."""
        if tick > self._last_tick:
            m = (int(move[0]), int(move[1])) if move else (0, 0)
            self._log[tick] = (m, action)
            self._last_tick = tick
        return self._last_tick

    def _new_state(self) -> dict:
        return core.new_fight(seed=self.seed, **self.setup)

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

    def to_row(self, session_id: str) -> dict:
        log = {str(t): [m[0], m[1], a] for t, (m, a) in sorted(self._log.items())}
        return {
            "fight_id": self.fight_id,
            "session_id": session_id,
            "seed": self.seed,
            "setup_json": json.dumps(self.setup, sort_keys=True),
            "log_json": json.dumps(log),
            "last_tick": self._last_tick,
            "is_boss": int(self.is_boss),
            "fail_count": self.fail_count,
            "status": self.status,
        }

    @classmethod
    def from_row(cls, row) -> "FightSession":
        setup = json.loads(row["setup_json"])
        fight = cls(
            fight_id=row["fight_id"],
            seed=row["seed"],
            player_atk=setup["player_atk"],
            player_def=setup["player_def"],
            enemy_hp=setup["enemy_hp"],
            enemy_atk=setup["enemy_atk"],
            enemy_def=setup["enemy_def"],
            enemy_posture=setup["enemy_posture"],
            enemy_x=setup["enemy_x"],
            is_boss=bool(row["is_boss"]),
            behavior_table=setup.get("behavior_table"),
            fail_count=row["fail_count"],
            status=row["status"],
        )
        for tick, (mx, my, action) in json.loads(row["log_json"]).items():
            fight.record_input(int(tick), action, (mx, my))
        return fight

"""WS connection handler — the hardened protocol gateway + engine-first dispatch.

Handles: auth (first-message `hello`), seq anti-replay, HMAC verify, per-session
rate limiting, ping/pong, the generation tracker (force-clear a hung generation
after `GENERATION_TIMEOUT`), and the gameplay loop — typed `action` frames go
straight to the progression handlers, `fight_input`/`fight_submit` feed the
deterministic re-sim validator, and `talk` runs a simulated narrative (the
LangGraph director wires in when the LLM lands).
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import time
from collections.abc import Awaitable, Callable

from fastapi import WebSocket, WebSocketDisconnect
from langgraph.types import Command

from . import config
from . import protocol as P
from .game import progression
from .game import rules as R
from .game.fight import REJECT_LIMIT, SIM_VERSION, FightSession
from .persistence import SessionStore

_security_logger = logging.getLogger("heirs-of-the-abyss.security")

_narrative_state: dict[str, dict] = {}


def _mark_narration(session_id: str, complete: bool) -> None:
    if session_id:
        _narrative_state[session_id] = {"complete": complete}


FIGHT_PERSIST_EVERY_TICKS = 25

_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        from .agent.graph import build_graph

        _graph = build_graph()
    return _graph


async def _drop_thread(config: dict) -> None:
    checkpointer = getattr(_get_graph(), "checkpointer", None)
    thread_id = config.get("configurable", {}).get("thread_id")
    for name in ("adelete_thread", "delete_thread"):
        delete = getattr(checkpointer, name, None)
        if delete is None:
            continue
        try:
            outcome = delete(thread_id)
            if asyncio.iscoroutine(outcome):
                await outcome
        except Exception:
            pass
        return


def log_security_event(code: str, detail: str) -> None:
    """Telemetry hook: emit a structured log line for every rejected frame.

    Security-sensitive paths (auth failure, HMAC mismatch, seq replay, rate
    limit, oversized frame, malformed JSON) all route through here so operators
    can alert on anomalies without instrumenting each branch.
    """
    _security_logger.warning("security_event code=%s detail=%s", code, detail)


class TokenBucket:
    """Simple per-session message rate limiter (token bucket)."""

    def __init__(self, rate: float, capacity: int) -> None:
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last = time.monotonic()

    def allow(self) -> bool:
        now = time.monotonic()
        self.tokens = min(float(self.capacity), self.tokens + (now - self.last) * self.rate)
        self.last = now
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class GenerationTracker:
    """Tracks in-flight generations; force-clears a hung one after `timeout`.

    A generation is keyed by `narrative_id`. If its coroutine does not finish
    within `timeout`, `on_timeout(narrative_id)` is awaited (sending a terminal
    `error`), and the in-flight entry is always cleared.
    """

    def __init__(self, timeout: float, on_timeout: Callable[[str], Awaitable[None]]) -> None:
        self.timeout = timeout
        self.on_timeout = on_timeout
        self._in_flight: dict[str, asyncio.Task] = {}

    @property
    def in_flight(self) -> frozenset[str]:
        return frozenset(self._in_flight)

    def start(self, narrative_id: str, coro: Awaitable[None]) -> asyncio.Task:
        task = asyncio.create_task(self._run(narrative_id, coro))
        self._in_flight[narrative_id] = task
        return task

    async def _run(self, narrative_id: str, coro: Awaitable[None]) -> None:
        try:
            async with asyncio.timeout(self.timeout):
                await coro
        except TimeoutError:
            await self.on_timeout(narrative_id)
        finally:
            self._in_flight.pop(narrative_id, None)


class Connection:
    """One client connection: framing, auth, HMAC, seq, dispatch."""

    def __init__(
        self,
        websocket: WebSocket,
        *,
        dev_token: str | None = None,
        signing_enabled: bool | None = None,
        generation_timeout: float | None = None,
        message_rate: float | None = None,
        message_burst: int | None = None,
        store: SessionStore | None = None,
    ) -> None:
        self.ws = websocket
        self.dev_token = config.DEV_TOKEN if dev_token is None else dev_token
        self.signing_enabled = config.ENABLE_SIGNING if signing_enabled is None else signing_enabled
        self.generation_timeout = config.GENERATION_TIMEOUT if generation_timeout is None else generation_timeout
        self._limiter = TokenBucket(
            config.MESSAGE_RATE if message_rate is None else message_rate,
            config.MESSAGE_BURST if message_burst is None else message_burst,
        )
        self.authenticated = False
        self.session_id: str | None = None
        self.resume_token: str | None = None
        self.hmac_key: bytes | None = None
        self._session = None
        self._fights: dict[str, FightSession] = {}
        self._parked: dict | None = None
        self._in_seq = P.SeqTracker()
        self._out_seq = 0
        self._generations = GenerationTracker(self.generation_timeout, self._on_generation_timeout)
        self.store = store

    # ── lifecycle ──────────────────────────────────────────────────────────
    async def run(self) -> None:
        await self.ws.accept()
        try:
            async for raw in self.ws.iter_text():
                await self._handle_raw(raw)
        except (WebSocketDisconnect, RuntimeError):
            # RuntimeError fires when the server closes the connection
            # (starlette calls `receive()` on an already-closed WS).
            pass

    async def _handle_raw(self, raw: str) -> None:
        if P.frame_too_large(raw.encode("utf-8")):
            log_security_event("frame_too_large", "frame exceeds 64KB")
            await self.send_error("frame_too_large", "frame exceeds 64KB", recoverable=True)
            return

        try:
            frame = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            log_security_event("bad_json", "malformed JSON frame")
            await self.ws.close(code=1007)
            return

        err = P.validate_envelope(frame)
        if err == "unsupported_version":
            log_security_event("unsupported_version", f"version {frame.get('v')} unsupported")
            await self.send_error("unsupported_version", f"version {frame.get('v')} unsupported", recoverable=False)
            await self.ws.close(code=1008)
            return
        if err:
            log_security_event("frame_invalid", f"envelope invalid: {err}")
            await self.ws.close(code=1007)
            return

        type_ = frame["type"]
        id_ = frame["id"]
        seq = frame["seq"]
        payload = frame["payload"]

        # anti-replay: seq strictly increasing per direction
        if not self._in_seq.check(seq):
            log_security_event("seq_replay", f"seq {seq} <= last {self._in_seq.last}")
            await self.ws.close(code=1008)
            return

        # auth: first message must be `hello`
        if not self.authenticated:
            if type_ != "hello":
                log_security_event("auth_failed", "hello required first")
                await self.send_error("auth_failed", "hello required first", recoverable=False)
                await self.ws.close(code=1008)
                return

        # HMAC verify (post-welcome frames only)
        if self.hmac_key is not None and self.signing_enabled:
            sig = frame.get("hmac")
            if sig is None or not P.verify_frame(self.hmac_key, type_, id_, seq, payload, sig):
                log_security_event("hmac_invalid", f"HMAC mismatch on {type_}")
                await self.send_error("hmac_invalid", "HMAC mismatch", recoverable=True)
                return

        self._in_seq.record(seq)

        if not self._limiter.allow():
            log_security_event("rate_limited", "message rate exceeded")
            await self.send_error("rate_limited", "message rate exceeded", recoverable=True)
            return

        await self._dispatch(type_, id_, payload)

    # ── dispatch ───────────────────────────────────────────────────────────
    async def _dispatch(self, type_: str, id_: str, payload: dict) -> None:
        if type_ == "hello":
            await self._handle_hello(id_, payload)
        elif type_ == "ping":
            await self._send("pong", id_, {})
        elif type_ == "action":
            await self._handle_action(id_, payload)
        elif type_ == "decision":
            if self._parked is not None and payload.get("decision_id") == self._parked["thread_id"]:
                await self._resume_parked(payload)
                return
            err = P.decision_error(is_generating=bool(self._generations.in_flight), is_parked=self._parked is not None)
            await self.send_error(err, "no matching decision", recoverable=True)
        elif type_ == "resume":
            await self._handle_resume(payload)
        elif type_ == "fight_input":
            await self._handle_fight_input(id_, payload)
        elif type_ == "fight_submit":
            await self._handle_fight_submit(id_, payload)
        else:
            await self.send_error("rule_violation", f"unexpected frame type {type_}", recoverable=True)

    async def _handle_action(self, id_: str, payload: dict) -> None:
        action = payload.get("action", "")
        params = payload.get("params", {})
        if self._session is not None and self._session.terminal:
            await self.send_error("session_terminal", "your run is over", recoverable=False)
            return
        if action == "talk":
            if self._generations.in_flight:
                await self.send_error("busy", "a narration is already in flight", recoverable=True)
                return
            narrative_id = f"n-{secrets.token_urlsafe(6)}"
            _mark_narration(self.session_id, complete=False)
            self._generations.start(narrative_id, self._narrate(narrative_id, params.get("text", "")))
            return
        if action == "_test_hang":
            narrative_id = f"n-{secrets.token_urlsafe(6)}"
            self._generations.start(narrative_id, self._hang())
            return
        if self._session is None:
            await self.send_error("auth_failed", "no active session", recoverable=False)
            return
        try:
            if action == "descend":
                result = progression.descend(self._session)
            elif action == "rest":
                result = progression.rest(self._session)
            elif action == "return_home":
                result = progression.return_home(self._session)
            elif action == "shop":
                result = progression.shop(self._session, params.get("item_id", ""))
            elif action == "enter_room":
                result = progression.enter_room(self._session, params.get("room_index", 0))
            elif action == "attack":
                await self._begin_encounter(params.get("room_index", 0))
                return
            else:
                await self._send("turn_result", id_, {"action_id_echo": id_, "result": {}})
                return
        except progression.ProgressionError as e:
            await self.send_error(e.code, e.message, recoverable=True)
            return
        await self._send("turn_result", id_, {"action_id_echo": id_, "result": result})

    async def _handle_fight_input(self, id_: str, payload: dict) -> None:
        fight = self._fights.get(payload.get("fight_id", ""))
        if fight is None:
            await self.send_error("session_not_found", "unknown fight_id", recoverable=True)
            return
        if fight.status != "open":
            await self.send_error("rule_violation", f"fight already {fight.status}", recoverable=True)
            return
        if fight.expired:
            await self._resolve_flee(fight, "tick_limit")
            return

        entries: list[tuple[int, str, tuple[int, int]]] = []
        try:
            if payload.get("batch"):
                for item in payload["batch"]:
                    move = item.get("params", {}).get("move", [0, 0])
                    entries.append((int(item["tick"]), str(item["action"]), (int(move[0]), int(move[1]))))
            else:
                move = payload.get("params", {}).get("move", [0, 0])
                entries.append((int(payload["tick"]), str(payload["action"]), (int(move[0]), int(move[1]))))
        except (KeyError, TypeError, ValueError, IndexError):
            await self.send_error("frame_invalid", "malformed fight_input", recoverable=True)
            return

        last_tick = 0
        for tick, action, move in entries:
            last_tick = fight.record_input(tick, action, move)
        if last_tick % FIGHT_PERSIST_EVERY_TICKS == 0:
            await self._persist_fight(fight)
        await self._send("fight_input_ack", fight.fight_id, {"fight_id": fight.fight_id, "last_tick": last_tick})

    async def _handle_fight_submit(self, id_: str, payload: dict) -> None:
        fight = self._fights.get(payload["fight_id"])
        if fight is None:
            await self.send_error("session_not_found", "unknown fight_id", recoverable=True)
            return
        if fight.status != "open":
            await self.send_error("rule_violation", f"fight already {fight.status}", recoverable=True)
            return
        if fight.expired:
            await self._resolve_flee(fight, "tick_limit")
            return

        verified, outcome = fight.verify(payload["state_hash"], payload["sim_version"])
        if not verified:
            fight.fail_count += 1
            log_security_event("fight_verify_failed", f"{fight.fight_id} fails={fight.fail_count}")
            await self._persist_fight(fight, force=True)
            if fight.fail_count >= REJECT_LIMIT:
                await self._resolve_flee(fight, "reject_cap")
                return
            await self._send("fight_result", payload["fight_id"], {
                "fight_id": payload["fight_id"],
                "verified": False,
                "outcome": {**outcome, "fail_count": fight.fail_count},
                "rewards": {},
            })
            return

        rewards: dict = {}
        if outcome["ehp"] <= 0:
            fight.status = "won"
            if self._session is not None:
                rewards = progression.apply_fight_result(self._session, outcome, fight.is_boss)
                await self._save_session()
        elif outcome["php"] <= 0:
            fight.status = "lost"
            if self._session is not None:
                self._session.terminal = True
                await self._save_session()

        if fight.status != "open":
            await self._persist_fight(fight, force=True)

        await self._send("fight_result", payload["fight_id"], {
            "fight_id": payload["fight_id"],
            "verified": True,
            "outcome": outcome,
            "rewards": rewards,
        })
        if fight.status == "lost":
            await self._send("game_over", secrets.token_urlsafe(6), {"reason": "death"})

    async def _resolve_flee(self, fight: FightSession, reason: str) -> None:
        fight.status = "fled"
        log_security_event("fight_fled", f"{fight.fight_id} reason={reason}")
        await self._persist_fight(fight, force=True)
        await self._send("fight_result", fight.fight_id, {
            "fight_id": fight.fight_id,
            "verified": False,
            "outcome": {"reason": reason},
            "rewards": {},
        })

    async def _persist_fight(self, fight: FightSession, *, force: bool = False) -> None:
        if self.store is None or not self.session_id:
            return
        if not force and fight.status == "open" and fight.last_saved_tick == fight.last_tick:
            return
        fight.last_saved_tick = fight.last_tick
        await self.store.save_fight(fight.to_row(self.session_id))

    async def _save_session(self) -> None:
        if self.store is not None and self._session is not None:
            await self.store.save(self._session)

    async def _begin_encounter(self, room_index: int) -> None:
        session = self._session
        floor_index = session.current_floor
        thread_id = f"enc-{self.session_id}-{floor_index}-{room_index}-{secrets.token_urlsafe(4)}"
        config = {"configurable": {"thread_id": thread_id}}
        init = {
            "intent": "encounter_gen",
            "session_id": session.session_id,
            "seed": session.seed,
            "floor_index": floor_index,
            "room_index": room_index,
            "tier": R.sector_of(floor_index),
            "build_tags": list(session.player.build_tags),
        }
        try:
            result = await _get_graph().ainvoke(init, config)
        except Exception as exc:
            await _drop_thread(config)
            log_security_event("compose_failed", str(exc)[:120])
            await self.send_error("generation_failed", "encounter rite failed", recoverable=True)
            return
        pending = result.get("pending_decision")
        if pending:
            self._parked = {"thread_id": thread_id, "room_index": room_index}
            await self._send("decision_request", thread_id, {
                "decision_id": thread_id,
                "prompt": pending.get("prompt", ""),
                "options": pending.get("options", []),
            })
            return
        await self._spawn_fight_from_state(result, room_index, config)

    async def _resume_parked(self, payload: dict) -> None:
        parked = self._parked or {}
        option = payload.get("option_id", "")
        config = {"configurable": {"thread_id": parked["thread_id"]}}
        room_index = parked.get("room_index", 0)
        try:
            result = await _get_graph().ainvoke(Command(resume=option), config)
        except Exception as exc:
            self._parked = None
            await _drop_thread(config)
            log_security_event("decision_failed", str(exc)[:120])
            await self.send_error("generation_failed", "rite collapsed", recoverable=True)
            return
        self._parked = None
        await self._spawn_fight_from_state(result, room_index, config)

    async def _spawn_fight_from_state(self, result: dict, room_index: int, config: dict) -> None:
        await _drop_thread(config)
        if result.get("flee"):
            await self._send("turn_result", secrets.token_urlsafe(6), {
                "action_id_echo": "", "result": {"fled": True},
            })
            return

        variant = result.get("variant") if result.get("committed") else None
        floor_index = self._session.current_floor
        if variant is not None:
            stats = variant.get("stats", {})
            opp = {
                "max_hp": int(stats.get("max_hp", 40)),
                "attack": int(stats.get("attack", 8)),
                "defense": int(stats.get("defense", 2)),
                "posture": int(stats.get("posture", 80)),
            }
            seed = progression.fight_seed(self._session.seed, floor_index, room_index)
            fight = FightSession(
                fight_id=f"f-{secrets.token_urlsafe(6)}",
                seed=seed,
                player_atk=self._session.player.attack,
                player_def=self._session.player.defense,
                enemy_hp=opp["max_hp"],
                enemy_atk=opp["attack"],
                enemy_def=opp["defense"],
                enemy_posture=opp["posture"],
                behavior_table=variant.get("behavior_table") or None,
            )
            spec = {
                "fight_id": fight.fight_id,
                "seed": seed,
                "sim_version": SIM_VERSION,
                "opponent_spec": {"stats": opp, "is_boss": False, "composed": True,
                                   "behavior_table": variant.get("behavior_table") or []},
                "player_spec": {"attack": self._session.player.attack,
                                 "defense": self._session.player.defense},
                "room_id": str(room_index),
            }
        else:
            fight, spec = progression.start_fight(self._session, room_index)

        self._fights[fight.fight_id] = fight
        await self._persist_fight(fight, force=True)
        await self._send("fight_begin", fight.fight_id, spec)

    async def _simulated_narrative(self, narrative_id: str) -> None:
        await asyncio.sleep(0.05)
        await self._send("narrative_delta", narrative_id, {"narrative_id": narrative_id, "text": "The door creaks."})
        await self._send("narrative_end", narrative_id, {"narrative_id": narrative_id})

    async def _narrate(self, narrative_id: str, player_text: str) -> None:
        build_tags = list(self._session.player.build_tags) if self._session else []
        floor_index = self._session.current_floor if self._session else 1
        config = {"configurable": {"thread_id": f"nar-{self.session_id}-{narrative_id}"}}
        try:
            result = await _get_graph().ainvoke(
                {
                    "intent": "narrate",
                    "session_id": self.session_id or "",
                    "current_floor": floor_index,
                    "player_text": player_text,
                    "build_tags": build_tags,
                },
                config,
            )
            text = result.get("narrative", "")
        except Exception:
            text = "The dungeon is silent."
        finally:
            await _drop_thread(config)
        await self._send("narrative_delta", narrative_id, {"narrative_id": narrative_id, "text": text})
        await self._send("narrative_end", narrative_id, {"narrative_id": narrative_id})
        _mark_narration(self.session_id, complete=True)

    async def _hang(self) -> None:
        await asyncio.Event().wait()

    async def _handle_hello(self, id_: str, payload: dict) -> None:
        if payload.get("token") != self.dev_token:
            log_security_event("auth_failed", "invalid token")
            await self.send_error("auth_failed", "invalid token", recoverable=False)
            await self.ws.close(code=1008)
            return
        self.authenticated = True
        self.session_id = f"s-{secrets.token_urlsafe(8)}"
        self.resume_token = secrets.token_urlsafe(P.RESUME_TOKEN_BYTES)
        self.hmac_key = secrets.token_bytes(32)
        session = self._new_session()
        self._session = session
        if self.store is not None:
            await self.store.create(session)
        await self._send(
            "welcome",
            self.session_id,
            {
                "session_id": self.session_id,
                "resume_token": self.resume_token,
                "hmac_key": self.hmac_key.hex(),
            },
            signed=False,
        )

    def _new_session(self):
        from .game.catalog import get_class
        from .game.models import GameSession, Player

        cls = get_class("brawler")
        stats = cls["stats"]
        player = Player(
            hp=stats["max_hp"], max_hp=stats["max_hp"],
            attack=stats["attack"], defense=stats["defense"],
            class_tag=cls["class_tag"],
        )
        player.recompute_build_tags()
        return GameSession(
            session_id=self.session_id or "",
            resume_token=self.resume_token or "",
            seed=secrets.randbelow(2**32),
            player=player,
        )

    async def _handle_resume(self, payload: dict) -> None:
        if self.store is None:
            await self.send_error("session_not_found", "no session store", recoverable=True)
            return
        session = await self.store.get_by_resume_token(payload.get("resume_token", ""))
        if session is None:
            await self.send_error("session_not_found", "session not found", recoverable=True)
            return
        self.session_id = session.session_id
        self.resume_token = session.resume_token
        self._session = session
        if self.store is not None:
            for row in await self.store.open_fights(self.session_id):
                fight = FightSession.from_row(row)
                self._fights[fight.fight_id] = fight
                fight.last_saved_tick = fight.last_tick
        await self._send("state_sync", self.session_id, {
            "seq": self._out_seq,
            "frame_index": 1,
            "frame_total": 1,
            "state": session.model_dump(),
        })
        state = _narrative_state.pop(self.session_id, None)
        if state is not None and not state.get("complete", True):
            await self._send(
                "narrative_replay",
                f"nr-{secrets.token_urlsafe(6)}",
                {"narrative_id": "", "offset": 0},
            )

    # ── send helpers ───────────────────────────────────────────────────────
    async def _send(self, type_: str, id_: str, payload: dict, signed: bool | None = None) -> None:
        if signed is None:
            signed = self.hmac_key is not None and self.signing_enabled
        frame: dict = {"v": P.PROTOCOL_VERSION, "type": type_, "id": id_, "seq": self._out_seq, "payload": payload}
        if signed and self.hmac_key is not None:
            frame["hmac"] = P.sign_frame(self.hmac_key, type_, id_, self._out_seq, payload)
        self._out_seq += 1
        await self.ws.send_text(json.dumps(frame, separators=(",", ":")))

    async def send_error(
        self, code: str, message: str, *, recoverable: bool = True, narrative_id: str | None = None
    ) -> None:
        await self._send(
            "error",
            secrets.token_urlsafe(6),
            {"code": code, "message": message, "recoverable": recoverable, "narrative_id": narrative_id},
        )

    async def _on_generation_timeout(self, narrative_id: str) -> None:
        await self.send_error("generation_failed", "generation timed out", narrative_id=narrative_id)

    # ── test/dev hook ──────────────────────────────────────────────────────
    def start_generation(self, narrative_id: str, coro: Awaitable[None]) -> asyncio.Task:
        """Start a simulated generation tracked by the timeout guard."""
        return self._generations.start(narrative_id, coro)

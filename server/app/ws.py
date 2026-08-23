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

from . import config
from . import protocol as P
from .game import progression
from .game.fight import FightSession
from .persistence import SessionStore

_security_logger = logging.getLogger("endlessdungeon.security")


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
            err = P.decision_error(is_generating=bool(self._generations.in_flight), is_parked=False)
            await self.send_error(err, "no pending decision", recoverable=True)
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
        if action == "talk":
            narrative_id = f"n-{secrets.token_urlsafe(6)}"
            self._generations.start(narrative_id, self._simulated_narrative(narrative_id))
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
            elif action == "attack":
                fight, spec = progression.start_fight(self._session, params.get("room_index", 0))
                self._fights[fight.fight_id] = fight
                await self._send("fight_begin", fight.fight_id, spec)
                return
            else:
                await self._send("turn_result", id_, {"action_id_echo": id_, "result": {}})
                return
        except progression.ProgressionError as e:
            await self.send_error(e.code, e.message, recoverable=True)
            return
        await self._send("turn_result", id_, {"action_id_echo": id_, "result": result})

    async def _handle_fight_input(self, id_: str, payload: dict) -> None:
        fight = self._fights.get(payload["fight_id"])
        if fight is None:
            await self.send_error("session_not_found", "unknown fight_id", recoverable=True)
            return
        move = payload.get("params", {}).get("move", [0, 0])
        last_tick = fight.record_input(payload["tick"], payload["action"], move)
        await self._send("fight_input_ack", payload["fight_id"], {"fight_id": payload["fight_id"], "last_tick": last_tick})

    async def _handle_fight_submit(self, id_: str, payload: dict) -> None:
        fight = self._fights.get(payload["fight_id"])
        if fight is None:
            await self.send_error("session_not_found", "unknown fight_id", recoverable=True)
            return
        verified, outcome = fight.verify(payload["state_hash"], payload["sim_version"])
        rewards = {}
        if verified and self._session is not None:
            rewards = progression.apply_fight_result(self._session, outcome)
        await self._send("fight_result", payload["fight_id"], {
            "fight_id": payload["fight_id"],
            "verified": verified,
            "outcome": outcome,
            "rewards": rewards,
        })

    async def _simulated_narrative(self, narrative_id: str) -> None:
        await asyncio.sleep(0.05)
        await self._send("narrative_delta", narrative_id, {"narrative_id": narrative_id, "text": "The door creaks."})
        await self._send("narrative_end", narrative_id, {"narrative_id": narrative_id})

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
        await self._send("state_sync", self.session_id, {
            "seq": self._out_seq,
            "frame_index": 1,
            "frame_total": 1,
            "state": session.model_dump(),
        })

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

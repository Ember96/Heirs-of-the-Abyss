"""EndlessDungeon WS v1 protocol — Python reference implementation.

Mirrors ``docs/05-protocol.md`` exactly. T1.3 wires this into the FastAPI WS
handler; T1.4 adds the GDScript HMAC mirror + the cross-language conformance test.

Frame envelope: ``{v, type, id, seq, payload, hmac?}``.
"""

from __future__ import annotations

import hashlib
import hmac as _hmac
import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError

# ── constants ────────────────────────────────────────────────────────────────
PROTOCOL_VERSION = 1
MAX_FRAME_BYTES = 64 * 1024  # 64 KB — enforced on every frame; `state_sync` exempt (multi-frame)
HEARTBEAT_INTERVAL_S = 15.0  # client pings every 15s
HEARTBEAT_TIMEOUT_S = 45.0  # server drops after 45s silence
GENERATION_TIMEOUT_DEFAULT_S = 30.0
RESUME_TOKEN_BYTES = 32  # secrets.token_urlsafe(32)

CLIENT_MESSAGES = frozenset(
    {"hello", "action", "decision", "fight_input", "fight_submit", "resume", "ping"}
)
SERVER_MESSAGES = frozenset(
    {
        "welcome", "decision_request", "state_sync", "state_delta", "narrative_delta",
        "narrative_replay", "narrative_end", "turn_result", "fight_begin",
        "fight_input_ack", "fight_snapshot", "fight_result", "error", "pong", "game_over",
    }
)
ALL_MESSAGES = CLIENT_MESSAGES | SERVER_MESSAGES

ERROR_CODES = frozenset(
    {
        "unsupported_version", "frame_too_large", "rule_violation", "session_not_found",
        "session_terminal", "input_too_long", "generation_failed", "generation_not_ready",
        "busy", "auth_failed", "hmac_invalid", "rate_limited",
    }
)

ACTIONS = frozenset(
    {
        "move", "attack", "use_item", "rest", "return_home", "descend",
        "talk", "run", "shop", "equip", "drop",
    }
)
ENGINE_ACTIONS = ACTIONS - {"talk"}  # dispatched straight to the engine, never busy-rejected
GRAPH_ACTIONS = frozenset({"talk"})  # free-form intents that enter the LangGraph

# envelope `id` semantics per frame type (HMAC covers `id`, so its meaning is pinned)
ID_SEMANTICS: dict[str, str] = {
    "action": "action_id", "turn_result": "action_id", "state_delta": "action_id",
    "narrative_delta": "narrative_id", "narrative_replay": "narrative_id", "narrative_end": "narrative_id",
    "fight_input": "fight_id", "fight_input_ack": "fight_id", "fight_snapshot": "fight_id",
    "fight_submit": "fight_id", "fight_begin": "fight_id", "fight_result": "fight_id",
    "decision": "decision_id", "decision_request": "decision_id",
    "welcome": "session_id", "state_sync": "session_id",
}


# ── HMAC ─────────────────────────────────────────────────────────────────────
def canonical_json(obj: Any) -> str:
    """Deterministic JSON for HMAC input: compact, keys sorted, ascii-escaped."""
    return json.dumps(obj, separators=(",", ":"), sort_keys=True, ensure_ascii=True)


def sign_frame(hmac_key: bytes, type_: str, id_: str, seq: int, payload: dict[str, Any]) -> str:
    """HMAC-SHA256 over ``type|id|seq|payload`` → hex digest."""
    msg = f"{type_}|{id_}|{seq}|{canonical_json(payload)}".encode("utf-8")
    return _hmac.new(hmac_key, msg, hashlib.sha256).hexdigest()


def verify_frame(
    hmac_key: bytes, type_: str, id_: str, seq: int, payload: dict[str, Any], signature: str
) -> bool:
    expected = sign_frame(hmac_key, type_, id_, seq, payload)
    return _hmac.compare_digest(expected, signature)


# ── seq tracking (anti-replay, per direction) ───────────────────────────────
class SeqTracker:
    """Monotonic per-direction seq validator: rejects ``seq <= last_seen``."""

    def __init__(self) -> None:
        self._last = -1

    def check(self, seq: int) -> bool:
        return seq > self._last

    def record(self, seq: int) -> None:
        self._last = max(self._last, seq)

    @property
    def last(self) -> int:
        return self._last


# ── payload schemas ──────────────────────────────────────────────────────────
class _Payload(BaseModel):
    model_config = {"extra": "forbid"}


class HelloPayload(_Payload):
    token: str


class ActionPayload(_Payload):
    action: str
    params: dict[str, Any] = Field(default_factory=dict)


class DecisionPayload(_Payload):
    decision_id: str
    option_id: str


class FightInputPayload(_Payload):
    fight_id: str
    tick: int
    action: str
    params: dict[str, Any] = Field(default_factory=dict)


class FightSubmitPayload(_Payload):
    fight_id: str
    claimed_result: dict[str, Any]
    state_hash: str
    sim_version: str


class ResumePayload(_Payload):
    resume_token: str


class PingPayload(_Payload):
    pass


class WelcomePayload(_Payload):
    session_id: str
    resume_token: str
    hmac_key: str


class DecisionRequestPayload(_Payload):
    decision_id: str
    prompt: str
    options: list[dict[str, Any]]


class StateSyncPayload(_Payload):
    seq: int
    frame_index: int
    frame_total: int
    state: dict[str, Any] = Field(default_factory=dict)


class StateDeltaPayload(_Payload):
    seq: int
    action_id_echo: str
    delta: dict[str, Any] = Field(default_factory=dict)


class NarrativeDeltaPayload(_Payload):
    narrative_id: str
    text: str = ""


class NarrativeReplayPayload(_Payload):
    narrative_id: str
    offset: int


class NarrativeEndPayload(_Payload):
    narrative_id: str


class TurnResultPayload(_Payload):
    action_id_echo: str
    result: dict[str, Any] = Field(default_factory=dict)


class FightBeginPayload(_Payload):
    fight_id: str
    seed: int
    sim_version: str
    opponent_spec: dict[str, Any]
    room_id: str


class FightInputAckPayload(_Payload):
    fight_id: str
    last_tick: int


class FightSnapshotPayload(_Payload):
    fight_id: str
    tick: int
    state: dict[str, Any] = Field(default_factory=dict)


class FightResultPayload(_Payload):
    fight_id: str
    verified: bool
    outcome: dict[str, Any]
    rewards: dict[str, Any] = Field(default_factory=dict)


class ErrorPayload(_Payload):
    code: str
    message: str
    recoverable: bool
    narrative_id: str | None = None


class PongPayload(_Payload):
    pass


class GameOverPayload(_Payload):
    reason: str = "terminal"


PAYLOAD_MODELS: dict[str, type[BaseModel]] = {
    "hello": HelloPayload,
    "action": ActionPayload,
    "decision": DecisionPayload,
    "fight_input": FightInputPayload,
    "fight_submit": FightSubmitPayload,
    "resume": ResumePayload,
    "ping": PingPayload,
    "welcome": WelcomePayload,
    "decision_request": DecisionRequestPayload,
    "state_sync": StateSyncPayload,
    "state_delta": StateDeltaPayload,
    "narrative_delta": NarrativeDeltaPayload,
    "narrative_replay": NarrativeReplayPayload,
    "narrative_end": NarrativeEndPayload,
    "turn_result": TurnResultPayload,
    "fight_begin": FightBeginPayload,
    "fight_input_ack": FightInputAckPayload,
    "fight_snapshot": FightSnapshotPayload,
    "fight_result": FightResultPayload,
    "error": ErrorPayload,
    "pong": PongPayload,
    "game_over": GameOverPayload,
}


# ── validation ───────────────────────────────────────────────────────────────
def validate_envelope(frame: dict[str, Any]) -> str | None:
    """Validate the envelope shape; return an error code, or None if valid."""
    if not isinstance(frame, dict):
        return "frame_invalid"
    if frame.get("v") != PROTOCOL_VERSION:
        return "unsupported_version"
    type_ = frame.get("type")
    if type_ not in ALL_MESSAGES:
        return "frame_invalid"
    if not isinstance(frame.get("id"), str) or frame["id"] == "":
        return "frame_invalid"
    seq = frame.get("seq")
    if not isinstance(seq, int) or seq < 0:
        return "frame_invalid"
    if not isinstance(frame.get("payload"), dict):
        return "frame_invalid"
    return None


def validate_payload(type_: str, payload: dict[str, Any]) -> str | None:
    """Validate a payload against its schema; return an error code, or None."""
    model = PAYLOAD_MODELS.get(type_)
    if model is None:
        return "frame_invalid"
    try:
        model(**payload)
    except ValidationError:
        return "frame_invalid"
    return None


def frame_too_large(raw: bytes) -> bool:
    return len(raw) > MAX_FRAME_BYTES


def decision_error(is_generating: bool, is_parked: bool) -> str | None:
    """Response for an out-of-context `decision` message.

    `decision` is valid only while parked at an interrupt. While a generation is
    in flight → `busy`; otherwise (no pending decision) → `rule_violation`.
    """
    if is_generating:
        return "busy"
    if not is_parked:
        return "rule_violation"
    return None

"""Conformance tests for the hardened v1 WS protocol (T1.2).

Covers: example-frame schema validation, HMAC sign/verify + tamper detection,
monotonic seq (anti-replay), 64KB frame cap, out-of-context decision, and the
resume ordering rules — all against ``app.protocol``.
"""

from __future__ import annotations

import json

import pytest

from app.protocol import (
    ACTIONS,
    ENGINE_ACTIONS,
    GRAPH_ACTIONS,
    ID_SEMANTICS,
    MAX_FRAME_BYTES,
    PROTOCOL_VERSION,
    SeqTracker,
    canonical_json,
    decision_error,
    frame_too_large,
    sign_frame,
    validate_envelope,
    validate_payload,
    verify_frame,
)

KEY = b"0123456789abcdef0123456789abcdef"  # 32 bytes


# ── example frames (one valid payload per message type) ─────────────────────
CLIENT_FRAMES = [
    ("hello", "s1", {"token": "dev-token"}),
    ("action", "a1", {"action": "move", "params": {"dx": 1, "dy": 0}}),
    ("decision", "d1", {"decision_id": "d1", "option_id": "o2"}),
    ("fight_input", "f1", {"fight_id": "f1", "tick": 120, "action": "attack", "params": {}}),
    ("fight_submit", "f1", {"fight_id": "f1", "claimed_result": {"hp": 100}, "state_hash": "abc123", "sim_version": "1.0.0"}),
    ("resume", "r1", {"resume_token": "resume-tok"}),
    ("ping", "p1", {}),
]

SERVER_FRAMES = [
    ("welcome", "s1", {"session_id": "s1", "resume_token": "resume-tok", "hmac_key": "hmac-secret"}),
    ("decision_request", "d1", {"decision_id": "d1", "prompt": "choose", "options": [{"option_id": "o1", "label": "A"}]}),
    ("state_sync", "s1", {"seq": 10, "frame_index": 1, "frame_total": 1, "state": {}}),
    ("state_delta", "a1", {"seq": 11, "action_id_echo": "a1", "delta": {}}),
    ("narrative_delta", "n1", {"narrative_id": "n1", "text": "The door creaks."}),
    ("narrative_replay", "n1", {"narrative_id": "n1", "offset": 0}),
    ("narrative_end", "n1", {"narrative_id": "n1"}),
    ("turn_result", "a1", {"action_id_echo": "a1", "result": {}}),
    ("fight_begin", "f1", {"fight_id": "f1", "seed": 42, "sim_version": "1.0.0", "opponent_spec": {}, "room_id": "r1"}),
    ("fight_input_ack", "f1", {"fight_id": "f1", "last_tick": 120}),
    ("fight_snapshot", "f1", {"fight_id": "f1", "tick": 120, "state": {}}),
    ("fight_result", "f1", {"fight_id": "f1", "verified": True, "outcome": {}, "rewards": {}}),
    ("error", "e1", {"code": "busy", "message": "still thinking", "recoverable": True}),
    ("pong", "p1", {}),
    ("game_over", "g1", {"reason": "terminal"}),
]


# ── envelope ─────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("type_,id_,payload", CLIENT_FRAMES + SERVER_FRAMES)
def test_example_frames_validate(type_, id_, payload):
    frame = {"v": PROTOCOL_VERSION, "type": type_, "id": id_, "seq": 0, "payload": payload}
    assert validate_envelope(frame) is None
    assert validate_payload(type_, payload) is None


def test_wrong_version_rejected():
    frame = {"v": 2, "type": "ping", "id": "p1", "seq": 0, "payload": {}}
    assert validate_envelope(frame) == "unsupported_version"


def test_unknown_type_rejected():
    frame = {"v": 1, "type": "nope", "id": "x", "seq": 0, "payload": {}}
    assert validate_envelope(frame) == "frame_invalid"


def test_missing_id_rejected():
    frame = {"v": 1, "type": "ping", "seq": 0, "payload": {}}
    assert validate_envelope(frame) == "frame_invalid"


def test_negative_seq_rejected():
    frame = {"v": 1, "type": "ping", "id": "p1", "seq": -1, "payload": {}}
    assert validate_envelope(frame) == "frame_invalid"


def test_extra_payload_field_forbidden():
    # `extra="forbid"` — a forged/extra field must be rejected
    assert validate_payload("hello", {"token": "t", "injected": "x"}) == "frame_invalid"


def test_action_types_are_closed_set():
    assert GRAPH_ACTIONS == {"talk"}
    assert ENGINE_ACTIONS == ACTIONS - {"talk"}
    assert "move" in ENGINE_ACTIONS and "talk" not in ENGINE_ACTIONS


# ── HMAC ─────────────────────────────────────────────────────────────────────
def test_hmac_roundtrip():
    payload = {"action": "move", "params": {"dx": 1}}
    sig = sign_frame(KEY, "action", "a1", 7, payload)
    assert verify_frame(KEY, "action", "a1", 7, payload, sig)


def test_hmac_tampered_payload_rejected():
    sig = sign_frame(KEY, "action", "a1", 7, {"action": "move", "params": {}})
    # different payload → different signature
    assert not verify_frame(KEY, "action", "a1", 7, {"action": "attack", "params": {}}, sig)


def test_hmac_tampered_seq_rejected():
    sig = sign_frame(KEY, "action", "a1", 7, {"action": "move", "params": {}})
    # replayed/edited seq → HMAC no longer matches
    assert not verify_frame(KEY, "action", "a1", 8, {"action": "move", "params": {}}, sig)


def test_hmac_wrong_key_rejected():
    sig = sign_frame(KEY, "ping", "p1", 1, {})
    assert not verify_frame(b"other-key-other-key-other-key", "ping", "p1", 1, {}, sig)


def test_canonical_json_is_deterministic():
    a = {"b": 1, "a": [2, 3]}
    b = {"a": [2, 3], "b": 1}
    assert canonical_json(a) == canonical_json(b)


# ── seq (anti-replay) ────────────────────────────────────────────────────────
def test_seq_monotonic_accepts_increasing():
    t = SeqTracker()
    assert t.check(0) and t.check(1) and t.check(2)
    t.record(0); t.record(1); t.record(2)
    assert t.last == 2


def test_seq_replay_rejected():
    t = SeqTracker()
    t.record(5)
    assert not t.check(5)   # equal → replay
    assert not t.check(3)   # older → replay
    assert t.check(6)       # newer → ok


# ── frame size cap ───────────────────────────────────────────────────────────
def test_frame_size_cap():
    small = b'{"v":1,"type":"ping"}' + b" " * 10
    big = b'{"v":1,"type":"ping"}' + b" " * MAX_FRAME_BYTES
    assert not frame_too_large(small)
    assert frame_too_large(big)


# ── out-of-context decision ──────────────────────────────────────────────────
def test_decision_during_generation_is_busy():
    assert decision_error(is_generating=True, is_parked=True) == "busy"


def test_decision_without_pending_decision_is_rule_violation():
    assert decision_error(is_generating=False, is_parked=False) == "rule_violation"


def test_decision_while_parked_is_valid():
    assert decision_error(is_generating=False, is_parked=True) is None


# ── resume ordering + id semantics (documented invariants) ──────────────────
def test_state_sync_is_session_scoped_and_final_frame_rule():
    # state_sync: envelope id = session_id; client applies ONLY when frame_index == frame_total
    assert ID_SEMANTICS["state_sync"] == "session_id"
    p = {"seq": 10, "frame_index": 2, "frame_total": 2, "state": {}}
    assert validate_payload("state_sync", p) is None
    assert p["frame_index"] == p["frame_total"]  # final frame of a 2-frame snapshot


def test_id_semantics_pinned():
    assert ID_SEMANTICS["action"] == "action_id"
    assert ID_SEMANTICS["narrative_delta"] == "narrative_id"
    assert ID_SEMANTICS["fight_submit"] == "fight_id"
    assert ID_SEMANTICS["decision"] == "decision_id"
    assert ID_SEMANTICS["welcome"] == "session_id"


def test_fight_submit_has_no_input_log():
    # B1 (round-5 blocker): fight_submit must NOT carry the full input log
    assert validate_payload("fight_submit", {"fight_id": "f", "claimed_result": {}, "state_hash": "h", "sim_version": "1"}) is None
    assert validate_payload("fight_submit", {"fight_id": "f", "claimed_result": {}, "state_hash": "h", "sim_version": "1", "input_log": []}) == "frame_invalid"

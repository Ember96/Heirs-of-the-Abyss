"""T7.1–T7.4 — durable fight lifecycle: persistence, death, reject cap, flee, boss gate."""

from __future__ import annotations

import json

import pytest

from app.game import rules as R
from app.game import progression
from app.game.fight import FightSession, state_hash
from app.game.models import GameSession, Player
from app.game.sim import core
from app.persistence import SessionStore
from app.ws import Connection


class FakeWS:
    def __init__(self):
        self.sent: list[str] = []

    async def send_text(self, text: str):
        self.sent.append(text)

    async def accept(self):
        pass

    async def close(self, code=1000):
        pass


def _frames(conn) -> list[dict]:
    return [json.loads(s) for s in conn.ws.sent]


def _session(sid="s1", token="rt1") -> GameSession:
    p = Player(hp=100, max_hp=100, attack=10, defense=5, class_tag="brawler")
    p.recompute_build_tags()
    return GameSession(session_id=sid, resume_token=token, seed=42, player=p)


def _conn(store: SessionStore | None, session: GameSession | None) -> Connection:
    conn = Connection(FakeWS(), store=store, signing_enabled=False)
    conn.authenticated = True
    if session is not None:
        conn.session_id = session.session_id
        conn._session = session
    return conn


def _fight(fid="f-x", **over) -> FightSession:
    base = dict(fight_id=fid, seed=7, player_atk=99, player_def=50, enemy_hp=5,
                enemy_atk=1, enemy_def=0, enemy_posture=10, enemy_x=0)
    base.update(over)
    return FightSession(**base)


def _client_sim(fight: FightSession, entries) -> dict:
    """Mirror the client: same core, same seed/setup, feed inputs, return final state."""
    sim_kwargs = {k: v for k, v in fight.setup.items() if k != "behavior_table"}
    state = core.new_fight(seed=fight.seed, **sim_kwargs)
    for move, action in entries:
        state, _ = core.step(state, move, action)
        fight.record_input(state["tick"], action, list(move))
    return state


async def _input(conn: Connection, fid: str, tick: int, action: str, move=(0, 0)) -> None:
    await conn._handle_fight_input("i", {
        "fight_id": fid, "tick": tick, "action": action, "params": {"move": list(move)},
    })


async def _submit(conn: Connection, fid: str, state: dict) -> None:
    await conn._handle_fight_submit("s", {
        "fight_id": fid,
        "claimed_result": {"php": state["php"], "ehp": state["ehp"]},
        "state_hash": state_hash(state),
        "sim_version": "1",
    })


@pytest.mark.asyncio
async def test_crash_restart_resumes_same_fight(tmp_path):
    store = SessionStore(tmp_path / "t.db")
    sess = _session()
    await store.create(sess)

    c1 = _conn(store, sess)
    c1._fights["f-x"] = _fight()
    await _input(c1, "f-x", 1, "attack")
    await c1._persist_fight(c1._fights["f-x"], force=True)  # debounced flush before the crash

    c2 = _conn(store, sess)
    await c2._handle_resume({"resume_token": sess.resume_token})
    types = [f["type"] for f in _frames(c2)]
    assert types[0] == "state_sync"
    resumed = c2._fights.get("f-x")
    assert resumed is not None and resumed.last_tick == 1 and resumed.status == "open"

    state = _client_sim(resumed, [((0, 0), "attack")])
    await _submit(c2, "f-x", state)

    result = _frames(c2)[-1]
    assert result["type"] == "fight_result" and result["payload"]["verified"] is True
    assert result["payload"]["rewards"]["gold"] == 20
    row = await store.load_fight("f-x")
    assert row["status"] == "won"


@pytest.mark.asyncio
async def test_death_sets_terminal_and_emits_game_over(tmp_path):
    store = SessionStore(tmp_path / "t.db")
    sess = _session()
    await store.create(sess)
    conn = _conn(store, sess)
    conn._fights["f-die"] = _fight(
        "f-die", player_atk=1, player_def=0, enemy_hp=999,
        enemy_atk=50, enemy_def=0, enemy_posture=999,
    )
    die = conn._fights["f-die"]
    sim_kwargs = {k: v for k, v in die.setup.items() if k != "behavior_table"}
    state = core.new_fight(seed=die.seed, **sim_kwargs)
    tick = 0
    while state["php"] > 0 and tick < R.FIGHT_TICK_LIMIT:
        state, _ = core.step(state, (0, 0), "none")
        tick += 1
        await _input(conn, "f-die", state["tick"], "none")
    assert state["php"] <= 0

    await _submit(conn, "f-die", state)
    tail = [f["type"] for f in _frames(conn)][-2:]
    assert tail == ["fight_result", "game_over"]
    game_over = _frames(conn)[-1]
    assert game_over["payload"]["reason"] == "death"
    assert conn._session.terminal is True
    stored = await store.get(sess.session_id)
    assert stored.terminal is True
    row = await store.load_fight("f-die")
    assert row["status"] == "lost"


@pytest.mark.asyncio
async def test_reject_cap_forces_flee():
    conn = _conn(None, _session())
    conn._fights["f-r"] = _fight("f-r")

    await _submit(conn, "f-r", {"php": 1, "ehp": 1})  # wrong hash #1
    first = _frames(conn)[-1]
    assert first["type"] == "fight_result" and first["payload"]["verified"] is False
    assert first["payload"]["outcome"]["fail_count"] == 1

    await _submit(conn, "f-r", {"php": 1, "ehp": 1})  # wrong hash #2 -> flee
    second = _frames(conn)[-1]
    assert second["payload"]["outcome"]["reason"] == "reject_cap"
    assert conn._fights["f-r"].status == "fled"


@pytest.mark.asyncio
async def test_tick_limit_forces_flee():
    conn = _conn(None, _session())
    fight = _fight("f-t")
    fight.record_input(R.FIGHT_TICK_LIMIT, "none", [0, 0])
    conn._fights["f-t"] = fight

    await _input(conn, "f-t", R.FIGHT_TICK_LIMIT + 1, "none")
    last = _frames(conn)[-1]
    assert last["type"] == "fight_result"
    assert last["payload"]["outcome"]["reason"] == "tick_limit"
    assert conn._fights["f-t"].status == "fled"


def test_boss_gate_blocks_descend_until_defeated():
    s = _session()
    s.current_floor = 5
    s.sector = 1
    with pytest.raises(progression.ProgressionError) as err:
        progression.descend(s)
    assert err.value.code == "rule_violation"

    s.bosses_defeated.append("the_violence")
    summary = progression.descend(s)
    assert summary["floor_index"] == 6


@pytest.mark.asyncio
async def test_terminal_session_rejects_actions():
    sess = _session()
    sess.terminal = True
    conn = _conn(None, sess)
    await conn._handle_action("a1", {"action": "descend", "params": {}})
    assert _frames(conn)[0]["payload"]["code"] == "session_terminal"

"""T2.5 — persistence round-trip, retention cascade, dedup, cache key."""

import time

import aiosqlite
import pytest

from app.game.models import GameSession, Player
from app.persistence import SessionStore


def _player():
    return Player(hp=100, max_hp=100, attack=10, defense=5, class_tag="brawler")


def _session(sid="s1", token="rt1"):
    return GameSession(session_id=sid, resume_token=token, seed=42, player=_player())


@pytest.fixture
def store(tmp_path):
    return SessionStore(tmp_path / "test.db")


@pytest.mark.asyncio
async def test_roundtrip(store):
    s = _session()
    await store.create(s)
    loaded = await store.get("s1")
    assert loaded == s


@pytest.mark.asyncio
async def test_get_by_resume_token(store):
    await store.create(_session())
    loaded = await store.get_by_resume_token("rt1")
    assert loaded is not None and loaded.session_id == "s1"


@pytest.mark.asyncio
async def test_save_updates_state(store):
    await store.create(_session())
    s = await store.get("s1")
    s.player.hp = 50
    s.terminal = True
    await store.save(s)
    loaded = await store.get("s1")
    assert loaded.player.hp == 50 and loaded.terminal is True


@pytest.mark.asyncio
async def test_dedup_window(store):
    assert await store.record_action("s1", "a1") is True
    assert await store.record_action("s1", "a1") is False
    assert await store.record_action("s1", "a2") is True


@pytest.mark.asyncio
async def test_cache_key_includes_session(store):
    await store.cache_set("s1", "v1", 1, 3, "hash", '{"x":1}', ttl=100.0)
    assert await store.cache_get("s2", "v1", 1, 3, "hash") is None
    assert await store.cache_get("s1", "v1", 1, 3, "hash") == '{"x":1}'


@pytest.mark.asyncio
async def test_retention_cascades_all_tables(store):
    await store.create(_session())
    await store.add_lore("s1", "a fragment", True)
    await store.record_action("s1", "a1")
    await store.cache_set("s1", "v1", 1, 3, "hash", "payload", ttl=100.0)

    conn = await aiosqlite.connect(store.db_path)
    await conn.execute("UPDATE sessions SET updated_at=? WHERE session_id=?", (time.time() - 40 * 86400, "s1"))
    await conn.commit()
    await conn.close()

    pruned = await store.prune_old_sessions()
    assert pruned == 1

    conn = await aiosqlite.connect(store.db_path)
    for table in ("sessions", "pregen_cache", "generated_lore", "action_ids"):
        async with conn.execute(f"SELECT COUNT(*) FROM {table}") as cursor:
            row = await cursor.fetchone()
            assert row[0] == 0, f"{table} not cleared"
    await conn.close()


@pytest.mark.asyncio
async def test_prune_oversized_evicts_oldest_first(tmp_path):
    import sqlite3
    import time as _time

    from app.game.models import GameSession, Player

    db = tmp_path / "big.db"
    store = SessionStore(db)

    def _mk(sid, token):
        p = Player(hp=1, max_hp=1, attack=1, defense=1, class_tag="brawler")
        return GameSession(session_id=sid, resume_token=token, seed=1, player=p)

    await store.create(_mk("old", "t-old"))
    _time.sleep(0.01)
    await store.create(_mk("new", "t-new"))

    conn = sqlite3.connect(db)
    new_sz = conn.execute("SELECT LENGTH(state_json) FROM sessions WHERE session_id='new'").fetchone()[0]
    conn.close()

    freed = await store.prune_oversized_sessions(max_bytes=new_sz + 16)

    assert freed == 1
    assert await store.get("old") is None
    assert await store.get("new") is not None

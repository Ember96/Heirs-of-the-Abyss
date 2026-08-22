"""SQLite persistence layer (T2.5) — WAL, aiosqlite, single-writer lock.

Tables: sessions, pregen_cache, generated_lore, action_ids. Retention cascades
a session delete across every store; the action-id dedup window is bounded.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import aiosqlite

from .game.models import GameSession

RETENTION_DAYS = 30
RETENTION_BYTES = 100 * 1024 * 1024
DEDUP_WINDOW = 100

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    resume_token TEXT UNIQUE NOT NULL,
    seed INTEGER NOT NULL,
    state_json TEXT NOT NULL,
    terminal INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS pregen_cache (
    session_id TEXT NOT NULL,
    content_version TEXT NOT NULL,
    seed INTEGER NOT NULL,
    floor_index INTEGER NOT NULL,
    build_hash TEXT NOT NULL,
    payload TEXT NOT NULL,
    ttl REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS generated_lore (
    session_id TEXT NOT NULL,
    fragment TEXT NOT NULL,
    is_generated INTEGER NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS action_ids (
    session_id TEXT NOT NULL,
    id TEXT NOT NULL,
    applied_at REAL NOT NULL
);
"""


class SessionStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._write_lock = asyncio.Lock()
        self._ready = False

    async def _connect(self) -> aiosqlite.Connection:
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row
        if not self._ready:
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.executescript(SCHEMA)
            self._ready = True
        return conn

    async def create(self, session: GameSession) -> None:
        now = time.time()
        async with self._write_lock:
            conn = await self._connect()
            await conn.execute(
                "INSERT OR REPLACE INTO sessions (session_id, resume_token, seed, state_json, terminal, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
                (session.session_id, session.resume_token, session.seed, session.model_dump_json(), int(session.terminal), now, now),
            )
            await conn.commit()
            await conn.close()

    async def get(self, session_id: str) -> GameSession | None:
        conn = await self._connect()
        async with conn.execute("SELECT state_json FROM sessions WHERE session_id=?", (session_id,)) as cursor:
            row = await cursor.fetchone()
        await conn.close()
        return GameSession.model_validate_json(row["state_json"]) if row else None

    async def get_by_resume_token(self, token: str) -> GameSession | None:
        conn = await self._connect()
        async with conn.execute("SELECT state_json FROM sessions WHERE resume_token=?", (token,)) as cursor:
            row = await cursor.fetchone()
        await conn.close()
        return GameSession.model_validate_json(row["state_json"]) if row else None

    async def save(self, session: GameSession) -> None:
        now = time.time()
        async with self._write_lock:
            conn = await self._connect()
            await conn.execute(
                "UPDATE sessions SET state_json=?, terminal=?, updated_at=? WHERE session_id=?",
                (session.model_dump_json(), int(session.terminal), now, session.session_id),
            )
            await conn.commit()
            await conn.close()

    async def delete(self, session_id: str) -> None:
        async with self._write_lock:
            conn = await self._connect()
            for table in ("pregen_cache", "generated_lore", "action_ids"):
                await conn.execute(f"DELETE FROM {table} WHERE session_id=?", (session_id,))
            await conn.execute("DELETE FROM sessions WHERE session_id=?", (session_id,))
            await conn.commit()
            await conn.close()

    async def record_action(self, session_id: str, action_id: str) -> bool:
        now = time.time()
        async with self._write_lock:
            conn = await self._connect()
            async with conn.execute("SELECT 1 FROM action_ids WHERE session_id=? AND id=?", (session_id, action_id)) as cursor:
                exists = await cursor.fetchone() is not None
            if exists:
                await conn.close()
                return False
            await conn.execute("INSERT INTO action_ids (session_id, id, applied_at) VALUES (?,?,?)", (session_id, action_id, now))
            await conn.execute(
                "DELETE FROM action_ids WHERE session_id=? AND rowid NOT IN (SELECT rowid FROM action_ids WHERE session_id=? ORDER BY applied_at DESC LIMIT ?)",
                (session_id, session_id, DEDUP_WINDOW),
            )
            await conn.commit()
            await conn.close()
            return True

    async def add_lore(self, session_id: str, fragment: str, is_generated: bool) -> None:
        async with self._write_lock:
            conn = await self._connect()
            await conn.execute(
                "INSERT INTO generated_lore (session_id, fragment, is_generated, created_at) VALUES (?,?,?,?)",
                (session_id, fragment, int(is_generated), time.time()),
            )
            await conn.commit()
            await conn.close()

    async def cache_set(self, session_id: str, content_version: str, seed: int, floor_index: int, build_hash: str, payload: str, ttl: float) -> None:
        async with self._write_lock:
            conn = await self._connect()
            await conn.execute(
                "INSERT INTO pregen_cache (session_id, content_version, seed, floor_index, build_hash, payload, ttl) VALUES (?,?,?,?,?,?,?)",
                (session_id, content_version, seed, floor_index, build_hash, payload, ttl),
            )
            await conn.commit()
            await conn.close()

    async def cache_get(self, session_id: str, content_version: str, seed: int, floor_index: int, build_hash: str) -> str | None:
        conn = await self._connect()
        async with conn.execute(
            "SELECT payload FROM pregen_cache WHERE session_id=? AND content_version=? AND seed=? AND floor_index=? AND build_hash=?",
            (session_id, content_version, seed, floor_index, build_hash),
        ) as cursor:
            row = await cursor.fetchone()
        await conn.close()
        return row["payload"] if row else None

    async def prune_old_sessions(self, max_age_days: int = RETENTION_DAYS) -> int:
        cutoff = time.time() - max_age_days * 86400
        async with self._write_lock:
            conn = await self._connect()
            async with conn.execute("SELECT session_id FROM sessions WHERE updated_at < ?", (cutoff,)) as cursor:
                old = [row["session_id"] async for row in cursor]
            for sid in old:
                for table in ("pregen_cache", "generated_lore", "action_ids"):
                    await conn.execute(f"DELETE FROM {table} WHERE session_id=?", (sid,))
                await conn.execute("DELETE FROM sessions WHERE session_id=?", (sid,))
            await conn.commit()
            await conn.close()
            return len(old)

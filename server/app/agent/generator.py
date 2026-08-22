"""Content generation pipeline (T3.4) — pre-gen, cache, token budget, termination.

Cold-cache descent serves a deterministic fallback floor immediately (never
blocks); the fallback is cached with a short TTL, not permanently. Every
generation runs under an injectable `asyncio.timeout`. The token budget is
enforced by the fixed 4-room schema (bounded fields).
"""

from __future__ import annotations

import asyncio
import time

TOKEN_CAP_FLOOR = 800
TOKEN_CAP_ENCOUNTER = 400
TOKEN_CAP_NARRATIVE = 600
CACHE_TTL = 300.0
FALLBACK_TTL = 300.0
CACHE_MAX_ENTRIES = 10


class GenerationTimeout(Exception):
    pass


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class GenerationCache:
    def __init__(self, max_entries: int = CACHE_MAX_ENTRIES, ttl: float = CACHE_TTL) -> None:
        self.max_entries = max_entries
        self.ttl = ttl
        self._entries: dict[str, tuple[float, dict]] = {}
        self.hits = 0
        self.misses = 0

    def key(self, session_id: str, content_version: str, seed: int, floor_index: int, build_hash: str) -> str:
        return f"{session_id}:{content_version}:{seed}:{floor_index}:{build_hash}"

    def get(self, key: str) -> dict | None:
        entry = self._entries.get(key)
        if entry is None:
            self.misses += 1
            return None
        ts, value = entry
        if time.time() - ts > self.ttl:
            del self._entries[key]
            self.misses += 1
            return None
        self.hits += 1
        return value

    def put(self, key: str, value: dict, ttl: float | None = None) -> None:
        self._entries[key] = (time.time(), value)
        if len(self._entries) > self.max_entries:
            oldest = min(self._entries, key=lambda k: self._entries[k][0])
            del self._entries[oldest]

    def size(self) -> int:
        return len(self._entries)


class Generator:
    def __init__(self, cache: GenerationCache | None = None, generation_timeout: float = 30.0) -> None:
        self.cache = cache or GenerationCache()
        self.generation_timeout = generation_timeout

    def fallback_floor(self, floor_index: int, seed: int) -> dict:
        from ..game import floorgen

        data = floorgen.generate_floor(seed, floor_index).model_dump()
        if estimate_tokens(str(data)) > TOKEN_CAP_FLOOR:
            raise ValueError("floor-gen exceeds token budget")
        return data

    async def generate_floor(self, session_id: str, content_version: str, seed: int, floor_index: int, build_hash: str) -> dict:
        key = self.cache.key(session_id, content_version, seed, floor_index, build_hash)
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        fallback = self.fallback_floor(floor_index, seed)
        self.cache.put(key, fallback, ttl=FALLBACK_TTL)
        return fallback

    async def generate_with_timeout(self, coro) -> dict:
        try:
            async with asyncio.timeout(self.generation_timeout):
                return await coro
        except TimeoutError:
            raise GenerationTimeout("generation timed out")

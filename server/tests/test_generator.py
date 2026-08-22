"""T3.4 — generation pipeline: cache, token budget, termination."""

import asyncio

import pytest

from app.agent.generator import (
    CACHE_MAX_ENTRIES,
    TOKEN_CAP_FLOOR,
    GenerationCache,
    GenerationTimeout,
    Generator,
    estimate_tokens,
)


@pytest.mark.asyncio
async def test_cache_hit_on_repeat():
    g = Generator()
    first = await g.generate_floor("s1", "v1", 42, 3, "hash")
    second = await g.generate_floor("s1", "v1", 42, 3, "hash")
    assert first == second
    assert g.cache.hits == 1
    assert g.cache.misses == 1


def test_cache_bounded_lru():
    cache = GenerationCache(max_entries=CACHE_MAX_ENTRIES)
    for i in range(15):
        cache.put(f"key{i}", {"floor": i})
    assert cache.size() <= CACHE_MAX_ENTRIES


def test_token_budget_enforced():
    g = Generator()
    data = g.fallback_floor(floor_index=3, seed=42)
    assert estimate_tokens(str(data)) <= TOKEN_CAP_FLOOR
    assert data["floor_index"] == 3


def test_fallback_floor_deterministic():
    g = Generator()
    assert g.fallback_floor(3, 42) == g.fallback_floor(3, 42)


@pytest.mark.asyncio
async def test_timeout_terminates_hung_generation():
    g = Generator(generation_timeout=0.05)

    async def slow():
        await asyncio.sleep(5.0)
        return {"done": True}

    with pytest.raises(GenerationTimeout):
        await g.generate_with_timeout(slow())


@pytest.mark.asyncio
async def test_generation_completes_within_timeout():
    g = Generator(generation_timeout=1.0)

    async def quick():
        return {"done": True}

    assert await g.generate_with_timeout(quick()) == {"done": True}

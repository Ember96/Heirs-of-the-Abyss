"""Seeded deterministic PRNG (Xorshift128+) — injectable everywhere.

No module-level `random` in sim paths: every random draw goes through an
explicit `SeededRandom` instance keyed by a stored seed.
"""

from __future__ import annotations

from typing import Sequence, TypeVar

T = TypeVar("T")


class SeededRandom:
    MASK = 0xFFFFFFFFFFFFFFFF

    def __init__(self, seed: int) -> None:
        s0 = self._splitmix64(seed)
        s1 = self._splitmix64(s0)
        self._s0 = s0 or 0x9E3779B97F4A7C15
        self._s1 = s1 or 0x9E3779B97F4A7C15

    @staticmethod
    def _splitmix64(x: int) -> int:
        x = (x + 0x9E3779B97F4A7C15) & SeededRandom.MASK
        x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & SeededRandom.MASK
        x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & SeededRandom.MASK
        return x ^ (x >> 31)

    def next_u64(self) -> int:
        x = self._s0
        y = self._s1
        self._s0 = y
        x ^= (x << 23) & self.MASK
        self._s1 = (x ^ y ^ (x >> 17) ^ (y >> 26)) & self.MASK
        return (self._s1 + y) & self.MASK

    def randint(self, lo: int, hi: int) -> int:
        return lo + (self.next_u64() % (hi - lo + 1))

    def random(self) -> float:
        return self.next_u64() / (self.MASK + 1)

    def choice(self, seq: Sequence[T]) -> T:
        return seq[self.randint(0, len(seq) - 1)]

    def shuffle(self, seq: Sequence[T]) -> list[T]:
        result = list(seq)
        for i in range(len(result) - 1, 0, -1):
            j = self.randint(0, i)
            result[i], result[j] = result[j], result[i]
        return result

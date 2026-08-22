"""T2.1 — SeededRandom determinism (Xorshift128+)."""

from app.game.rng import SeededRandom


def test_same_seed_same_sequence():
    a = SeededRandom(42)
    b = SeededRandom(42)
    assert [a.next_u64() for _ in range(100)] == [b.next_u64() for _ in range(100)]


def test_different_seed_different_sequence():
    a = SeededRandom(42)
    b = SeededRandom(43)
    assert [a.next_u64() for _ in range(10)] != [b.next_u64() for _ in range(10)]


def test_randint_bounds():
    r = SeededRandom(7)
    for _ in range(1000):
        assert 0 <= r.randint(0, 9) <= 9


def test_random_unit_interval():
    r = SeededRandom(7)
    for _ in range(1000):
        assert 0.0 <= r.random() < 1.0


def test_shuffle_deterministic():
    a = SeededRandom(42)
    b = SeededRandom(42)
    assert a.shuffle(list(range(10))) == b.shuffle(list(range(10)))

"""T2.4 — seeded floor generator invariants + determinism."""

import subprocess
from pathlib import Path

from app.game import floorgen, rules as R
from app.game.models import RoomType
from app.game.rng import SeededRandom


def test_same_seed_byte_identical_floor():
    a = floorgen.generate_floor(seed=7, floor_index=3)
    b = floorgen.generate_floor(seed=7, floor_index=3)
    assert a.model_dump() == b.model_dump()


def test_template_invariants_1000_seeds():
    for i in range(1000):
        f = floorgen.generate_floor(seed=i, floor_index=(i % 15) + 1)
        assert len(f.rooms) == R.ROOMS_PER_FLOOR
        assert sum(1 for r in f.rooms if r.type == RoomType.ENEMY) == R.ENEMY_ROOMS_PER_FLOOR


def test_boss_floor_and_shrine_floor():
    assert floorgen.choose_special(5, SeededRandom(1)) == RoomType.BOSS
    assert floorgen.choose_special(10, SeededRandom(1)) == RoomType.BOSS
    assert floorgen.choose_special(1, SeededRandom(1)) == RoomType.SHRINE
    assert floorgen.choose_special(6, SeededRandom(1)) == RoomType.SHRINE


def test_every_sector_has_loot_or_event():
    for sector in range(1, 20):
        for floor_index in range((sector - 1) * 5 + 2, sector * 5):  # floors 2-4
            pos = R.position_in_sector(floor_index)
            assert pos in (2, 3, 4)
            special = floorgen.choose_special(floor_index, SeededRandom(floor_index))
            assert special in (RoomType.LOOT, RoomType.EVENT)


def test_reachability_bfs():
    for i in range(100):
        f = floorgen.generate_floor(seed=i, floor_index=(i % 15) + 1)
        assert floorgen.reachable(f)


def test_pacing_band_1000_seeds():
    for i in range(1000):
        f = floorgen.generate_floor(seed=i, floor_index=(i % 15) + 1)
        assert floorgen.in_band(f), f"floor {f.floor_index} seed {i} out of band"


def test_place_enemy_is_sole_append_path():
    game_dir = Path(__file__).resolve().parent.parent / "app" / "game"
    result = subprocess.run(
        ["grep", "-rn", ".enemies.append", str(game_dir)], capture_output=True, text=True,
    )
    hits = [l for l in result.stdout.splitlines() if l.strip()]
    assert len(hits) == 1 and "floorgen.py" in hits[0], f"enemies.append outside place_enemy: {hits}"

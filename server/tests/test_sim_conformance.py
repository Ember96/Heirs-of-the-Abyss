"""T2.3 — sim core conformance: Python and GDScript are byte-identical."""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from app.game.rng import SeededRandom
from app.game.sim import core

CLIENT_DIR = Path(__file__).resolve().parent.parent.parent / "client"
ACTIONS = ["none", "attack", "roll", "block"]


def _cases(n: int) -> list[dict]:
    rnd = SeededRandom(99)
    cases = []
    for _ in range(n):
        cases.append({
            "seed": rnd.randint(0, 0xFFFFFFFF),
            "patk": 10, "pdef": 5,
            "ehp": rnd.randint(30, 120), "eatk": rnd.randint(5, 15), "edef": rnd.randint(0, 8),
            "epost": rnd.randint(80, 150), "ex": rnd.randint(500, 5000),
            "moves": [
                [rnd.randint(-1, 1) * 500, rnd.randint(-1, 1) * 500, ACTIONS[rnd.randint(0, 3)]]
                for _ in range(rnd.randint(30, 120))
            ],
        })
    return cases


def _python_results(cases):
    results = []
    for c in cases:
        s = core.new_fight(c["seed"], c["patk"], c["pdef"], c["ehp"], c["eatk"], c["edef"], c["epost"], c["ex"])
        for m in c["moves"]:
            s, _ = core.step(s, (m[0], m[1]), m[2])
        results.append(s)
    return results


def test_sim_deterministic_python():
    a, b = core.new_fight(seed=42), core.new_fight(seed=42)
    for i in range(500):
        a, _ = core.step(a, (0, 0), "attack" if i % 10 == 0 else "none")
        b, _ = core.step(b, (0, 0), "attack" if i % 10 == 0 else "none")
    assert a == b


def test_sim_conformance_python_gdscript():
    godot = shutil.which("godot")
    if not godot:
        pytest.skip("godot not on PATH")
    cases = _cases(50)
    py = _python_results(cases)
    inp = Path(tempfile.mktemp(suffix=".json"))
    out = Path(tempfile.mktemp(suffix=".json"))
    inp.write_text(json.dumps(cases), encoding="utf-8")
    subprocess.run(
        [godot, "--headless", "--path", str(CLIENT_DIR), "--script", "res://scripts/test_sim.gd", "--", str(inp), str(out)],
        capture_output=True, text=True, timeout=60,
    )
    gd = json.loads(out.read_text(encoding="utf-8"))
    inp.unlink(missing_ok=True)
    out.unlink(missing_ok=True)
    assert py == gd, "sim divergence between Python and GDScript"

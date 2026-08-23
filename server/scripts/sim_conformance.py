"""Sim conformance runner — proves the Python and GDScript sim cores are byte-identical.

Generates a deterministic corpus (>=2000 seeded cases), runs each through both
implementations, and asserts byte-identical final states. Commits the corpus to
catalog/sim_corpus/corpus.json.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from app.game.rng import SeededRandom
from app.game.sim import core

ROOT = Path(__file__).resolve().parent.parent.parent
CLIENT_DIR = ROOT / "client"
CORPUS_PATH = ROOT / "catalog" / "sim_corpus" / "corpus.json"

ACTIONS = ["none", "attack", "roll", "block"]


def generate_cases(n: int, seed: int = 12345) -> list[dict]:
    rnd = SeededRandom(seed)
    cases = []
    for _ in range(n):
        case = {
            "seed": rnd.randint(0, 0xFFFFFFFF),
            "patk": 10, "pdef": 5,
            "ehp": rnd.randint(30, 120), "eatk": rnd.randint(5, 15), "edef": rnd.randint(0, 8),
            "epost": rnd.randint(80, 150), "ex": rnd.randint(500, 5000),
            "moves": [
                [rnd.randint(-1, 1) * 500, rnd.randint(-1, 1) * 500, ACTIONS[rnd.randint(0, 3)]]
                for _ in range(rnd.randint(30, 120))
            ],
        }
        case["bt"] = []
        if rnd.randint(0, 1) == 0:
            for _ in range(rnd.randint(1, 3)):
                case["bt"].append({
                    "action": f"m{rnd.randint(0, 9)}",
                    "weight": rnd.randint(1, 4),
                    "damage": rnd.randint(3, 20),
                })
        cases.append(case)
    return cases


def run_python(cases: list[dict]) -> list[dict]:
    results = []
    for c in cases:
        state = core.new_fight(c["seed"], c["patk"], c["pdef"], c["ehp"], c["eatk"], c["edef"], c["epost"], c["ex"], c.get("bt", []))
        for m in c["moves"]:
            state, _ = core.step(state, (m[0], m[1]), m[2])
        results.append(state)
    return results


def run_gdscript(cases: list[dict]) -> list[dict]:
    godot = shutil.which("godot")
    if not godot:
        print("godot not on PATH")
        sys.exit(2)
    inp = Path(tempfile.mktemp(suffix=".json"))
    out = Path(tempfile.mktemp(suffix=".json"))
    inp.write_text(json.dumps(cases), encoding="utf-8")
    subprocess.run(
        [godot, "--headless", "--path", str(CLIENT_DIR), "--script", "res://scripts/test_sim.gd", "--", str(inp), str(out)],
        capture_output=True, text=True, timeout=120,
    )
    results = json.loads(out.read_text(encoding="utf-8"))
    inp.unlink(missing_ok=True)
    out.unlink(missing_ok=True)
    return results


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    cases = generate_cases(n)
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CORPUS_PATH.write_text(json.dumps(cases), encoding="utf-8")

    py = run_python(cases)
    gd = run_gdscript(cases)

    mismatches = [i for i, (p, g) in enumerate(zip(py, gd)) if p != g]
    if mismatches:
        print(f"FAILED: {len(mismatches)}/{n} cases diverge; first indices: {mismatches[:5]}")
        for i in mismatches[:2]:
            print(f"  case {i}:")
            print(f"    py = {py[i]}")
            print(f"    gd = {gd[i]}")
        return 1
    print(f"PASS: {n} cases byte-identical (Python == GDScript)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

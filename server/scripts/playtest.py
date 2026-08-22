"""Latency + cost verification runner (T6.2).

Run: cd server && uv run python scripts/playtest.py
"""

from __future__ import annotations

import sys

from app.evals.latency import LATENCY_BUDGETS, measure_re_sim_time
from app.game import rules as R


def main() -> int:
    re_sim = measure_re_sim_time()
    budget = LATENCY_BUDGETS["re_sim"]
    ok = re_sim < budget
    print(f"  re_sim ({R.FIGHT_TICK_LIMIT} ticks): {re_sim * 1000:.1f} ms (budget <{budget * 1000:.0f} ms) {'PASS' if ok else 'FAIL'}")
    print("  (turn p50/p95, TTFT, WS round-trip deferred — measured when LLM/server wired)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

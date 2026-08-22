"""T6.2 — fight re-simulation stays under budget."""

from app.evals.latency import LATENCY_BUDGETS, measure_re_sim_time


def test_re_sim_under_budget():
    assert measure_re_sim_time() < LATENCY_BUDGETS["re_sim"]

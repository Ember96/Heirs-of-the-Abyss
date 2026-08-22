"""T6.1 — eval gates pass thresholds."""

from app.evals.evaluators import THRESHOLDS, run_evals


def test_eval_gates_pass_thresholds():
    report = run_evals()
    assert report["schema_valid"] >= THRESHOLDS["schema_valid"]
    assert report["balance"] >= THRESHOLDS["balance"]
    assert report["catalog_ids"] >= THRESHOLDS["catalog_ids"]


def test_eval_main_returns_zero():
    from app.evals.evaluators import main

    assert main() == 0

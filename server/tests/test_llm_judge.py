"""LLM-judge eval tests (NFR-8) — mocked LLM responses, no API credits burned."""

from __future__ import annotations

from unittest.mock import patch

from app.evals import llm_judge
from app.evals.llm_judge import llm


def _mock_llm(score: float):
    import json

    def fake_complete(prompt, **kwargs):
        return json.dumps({"score": score})

    return fake_complete


def test_judge_narrative_high_score():
    with patch.object(llm_judge.llm, "complete", _mock_llm(92.0)):
        score = llm_judge.judge_narrative("The walls bleed.", 2, ["brawler"])
    assert score == 92.0


def test_judge_narrative_low_score():
    with patch.object(llm_judge.llm, "complete", _mock_llm(40.0)):
        score = llm_judge.judge_narrative("A hallway.", 1, ["brawler"])
    assert score == 40.0


def test_judge_rule_adherence_pass():
    with patch.object(llm_judge.llm, "complete", _mock_llm(97.0)):
        score = llm_judge.judge_rule_adherence({"enemy_id": "hound"}, ["brawler"])
    assert score == 97.0


def test_judge_no_key_returns_fallback(monkeypatch):
    monkeypatch.setattr(llm_judge.config, "OPENROUTER_API_KEY", "")
    score = llm_judge.judge_narrative("test", 1, [])
    assert score == 80.0  # fallback = narrative threshold


def test_judge_llm_error_returns_fallback(monkeypatch):
    def failing(prompt, **kw):
        raise llm.LLMError("api down")

    monkeypatch.setattr(llm_judge.llm, "complete", failing)
    score = llm_judge.judge_rule_adherence({"enemy_id": "hound"}, ["brawler"])
    assert score == 95.0  # fallback = rule-adherence threshold

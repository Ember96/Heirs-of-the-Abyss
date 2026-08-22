"""T5.2 — sim core discipline: no floats/random/timers in sim paths."""

from pathlib import Path

CLIENT_SCRIPTS = Path(__file__).resolve().parent.parent.parent / "client" / "scripts"


def test_sim_core_has_no_random_or_timers():
    text = (CLIENT_SCRIPTS / "sim_core.gd").read_text(encoding="utf-8")
    for banned in ("randf", "randi(", "randomize", "create_timer", "randf_range"):
        assert banned not in text, f"sim_core.gd contains forbidden '{banned}'"


def test_sim_core_uses_seeded_xorshift():
    text = (CLIENT_SCRIPTS / "sim_core.gd").read_text(encoding="utf-8")
    assert "xorshift32" in text


def test_sim_core_no_float_literals():
    text = (CLIENT_SCRIPTS / "sim_core.gd").read_text(encoding="utf-8")
    assert "1.5" not in text and "0.5" not in text

"""T5.3 — real-time combat: fight controller determinism, log, state_hash."""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

CLIENT_DIR = Path(__file__).resolve().parent.parent.parent / "client"


def test_fight_deterministic():
    godot = shutil.which("godot")
    if not godot:
        pytest.skip("godot not on PATH")
    out = Path(tempfile.mktemp(suffix=".txt"))
    subprocess.run(
        [godot, "--headless", "--path", str(CLIENT_DIR), "--script", "res://scripts/test_fight.gd", "--", str(out)],
        capture_output=True, text=True, timeout=60,
    )
    text = out.read_text(encoding="utf-8")
    out.unlink(missing_ok=True)
    assert "deterministic=true" in text
    assert "hash=" in text
    assert "log=" in text

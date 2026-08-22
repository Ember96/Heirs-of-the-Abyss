"""T5.4 — game scenes: narrative escaping, HUD ratios, boss-skill progression."""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

CLIENT_DIR = Path(__file__).resolve().parent.parent.parent / "client"


def test_scene_logic():
    godot = shutil.which("godot")
    if not godot:
        pytest.skip("godot not on PATH")
    out = Path(tempfile.mktemp(suffix=".txt"))
    subprocess.run(
        [godot, "--headless", "--path", str(CLIENT_DIR), "--script", "res://scripts/test_scenes.gd", "--", str(out)],
        capture_output=True, text=True, timeout=60,
    )
    text = out.read_text(encoding="utf-8")
    out.unlink(missing_ok=True)
    assert "escape=true" in text
    assert "hud=true" in text
    assert "unlock=true" in text
    assert "level=true" in text

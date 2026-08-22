"""T5.1 — isometric floor renderer determinism (same seed -> same layout)."""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

CLIENT_DIR = Path(__file__).resolve().parent.parent.parent / "client"


def test_floor_render_deterministic():
    godot = shutil.which("godot")
    if not godot:
        pytest.skip("godot not on PATH")
    out = Path(tempfile.mktemp(suffix=".txt"))
    subprocess.run(
        [godot, "--headless", "--path", str(CLIENT_DIR), "--script", "res://scripts/test_floor_render.gd", "--", str(out)],
        capture_output=True, text=True, timeout=60,
    )
    text = out.read_text(encoding="utf-8")
    out.unlink(missing_ok=True)
    assert "deterministic=true" in text
    assert "cells=96" in text

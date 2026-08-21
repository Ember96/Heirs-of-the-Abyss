"""Server configuration from environment variables (see `.env.example`)."""

from __future__ import annotations

import os


def _bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None:
        return default
    return float(value)


DEV_TOKEN = os.environ.get("DEV_TOKEN", "dev-secret-change-me")
ENABLE_SIGNING = _bool("ENABLE_SIGNING", True)
GENERATION_TIMEOUT = _float("GENERATION_TIMEOUT", 30.0)
MESSAGE_RATE = _float("MESSAGE_RATE", 50.0)  # msg/s per session
MESSAGE_BURST = int(os.environ.get("MESSAGE_BURST", "100"))

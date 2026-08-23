"""Server configuration from environment variables (see `.env.example`)."""

from __future__ import annotations

import os


def _load_dotenv() -> None:
    """Minimal .env loader (KEY=VALUE lines) — avoids a python-dotenv dependency."""
    root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
    path = os.path.join(root, ".env")
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


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

# ── LLM (OpenRouter — OpenAI-compatible) ──────────────────────────────────────
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openrouter")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
MODEL_FAST = os.environ.get("MODEL_FAST", "meta-llama/llama-3.1-8b-instruct")  # routing / judges
MODEL_CHAT = os.environ.get("MODEL_CHAT", "meta-llama/llama-3.3-70b-instruct")  # composition / narrative

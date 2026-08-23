"""OpenRouter LLM client (OpenAI-compatible) — cheap model routing.

`MODEL_FAST` drives routing/classification and the verifier judges; `MODEL_CHAT`
drives composition and narrative. Calls are synchronous; the WS layer runs them
in `asyncio.to_thread` so they never block the event loop.
"""

from __future__ import annotations

import httpx

from . import config


class LLMError(Exception):
    pass


def complete(
    prompt: str,
    *,
    system: str = "",
    model: str | None = None,
    max_tokens: int = 500,
    json_mode: bool = False,
) -> str:
    model = model or config.MODEL_CHAT
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    body: dict = {"model": model, "messages": messages, "max_tokens": max_tokens}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    resp = httpx.post(
        f"{config.OPENROUTER_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {config.OPENROUTER_API_KEY}"},
        json=body,
        timeout=config.GENERATION_TIMEOUT,
    )
    if resp.status_code != 200:
        raise LLMError(f"LLM error {resp.status_code}: {resp.text[:200]}")
    return resp.json()["choices"][0]["message"]["content"]

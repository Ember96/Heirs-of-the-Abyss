# Runbook

> Status: **complete** — quickstart, env vars, ops, and cost/latency expectations (T6.2/T6.4).

## Quickstart (< 15 min)

> [!TIP]
> Fresh clone → running stack in under 15 minutes.

```bash
# 1. Server
cd server && uv sync
cp ../.env.example ../.env          # set DEV_TOKEN; optionally LLM keys

# 2. Tests (must be green)
uv run pytest

# 3. Evals (T6.1)
uv run evals

# 4. Client
cd ../client && godot --path . --editor

# 5. Docs drift gate
cd ../server && uv run docs-check
```

## Environment variables

> [!NOTE]
> See `.env.example` for the full list. The table below is the operational subset.

| Var | Default | Notes |
|-----|---------|-------|
| `LLM_PROVIDER` | `openai` | `openai` / `anthropic` / `ollama` |
| `MODEL_CHAT` | `gpt-4o-mini` | composition / narrative |
| `MODEL_FAST` | `gpt-4o-mini` | routing / classification |
| `MODEL_EMBED` | `text-embedding-3-small` | RAG embeddings |
| `COHERE_API_KEY` | *(empty)* | embeddings for hybrid retrieval; empty = pure-BM25 fallback |
| `COHERE_EMBED_MODEL` | `embed-english-v3.0` | embedding model (1024 dims) |
| `DATABASE_URL` | `sqlite:///data/heirs-of-the-abyss.db` | game DB |
| `DEV_TOKEN` | `dev-secret-change-me` | must override (see caution) |
| `ENABLE_SIGNING` | `true` | per-session HMAC |
| `ENABLE_MODERATION` | `false` | content moderation hook |
| `GENERATION_TIMEOUT` | `30` | force-kill hung generation (s) |
| `LANGSMITH_TRACING` | `false` | trace when `LANGSMITH_API_KEY` set |

> [!CAUTION]
> Never ship the default `DEV_TOKEN`. Set a strong token and enforce TLS (`wss://`) in production — the HMAC key and resume token are bearer secrets.

## Provider switching

> [!NOTE]
> Switch providers by setting `LLM_PROVIDER` plus the matching key. `ollama` runs fully local (no API key); `openai`/`anthropic` need their API keys.

## Session ops

> [!NOTE]
> Sessions persist in SQLite (`DATABASE_URL`). A client reconnects with its `resume_token` and the server re-simulates the input log — the sim never re-rolls. Retention is enforced at every server start (sessions older than 30 days, oldest-first eviction until the 100 MB budget fits) and cascades across all per-session stores including fights.

## Latency + cost

> [!TIP]
> Measured (T6.2): worst-case full-fight re-simulation is **16 ms** (budget 1000 ms). LLM-dependent metrics (turn p50/p95, TTFT) are documented when the LLM is wired; budgets are p50 <3 s, p95 <8 s, TTFT <1.5 s, WS round-trip <100 ms.

## See also

- [Environment variables](../.env.example)
- [Security — hardening](13-security.md)
- [Evals — thresholds & runner](11-evals.md)

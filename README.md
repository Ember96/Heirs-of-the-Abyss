# EndlessDungeon

A single-player **soulslike roguelike** with unbounded AI-generated floors. A LangGraph "dungeon master" agent composes enemies, encounters, and narrative from your actions and character build — grounded in a game-design corpus, gated by four verification agents — while a deterministic Python engine owns all rules and combat. Godot 4 renders the isometric client.

> Status: **Wave 1 — foundation**. See [`specs/`](specs/) for the spec-driven plan (`spec.md` → `plan.md` → `tasks.md`) and [`docs/`](docs/) for the living documentation.

## Architecture (one line)

```
Godot 4.7 client (GDScript)  ⇄  FastAPI/WebSocket  ⇄  deterministic engine + LangGraph director + RAG (Qdrant)
```

The engine owns **all** stats, combat, and enemy AI. The LLM only emits validated JSON content. Combat is real-time, **dice-free**, and deterministic — the client simulates, the server re-simulates the input log to verify.

## Prerequisites

- **Python 3.12** + [uv](https://docs.astral.sh/uv/)
- **Godot 4.7.2** (on PATH as `godot`)
- **Node.js 20+** (for the optional Godot MCP)
- **Docker** (for Qdrant in Wave 4)

## Quickstart

```bash
# 1. Server
cd server
uv sync
cp ../.env.example ../.env          # fill in your LLM / LangSmith keys
uv run uvicorn app.main:app --reload   # (app.main lands in T1.3)

# 2. Tests
uv run pytest

# 3. Client
cd ../client
godot --path . --editor              # or open the folder in Godot 4.7.2

# 4. Docs drift gate (live from T1.6)
uv run docs:check
```

## Repository layout

```
server/   Python 3.12 (uv): FastAPI + LangGraph + Qdrant — engine, agent, RAG
client/   Godot 4.7.2 (GDScript): isometric renderer, NetworkManager, combat scenes
catalog/  content catalog + game-design corpus (see catalog/corpus/manifest.json)
docs/     living documentation (13 docs + Mermaid diagrams, docs:check drift gate)
specs/    spec-driven plan (spec.md → plan.md → tasks.md)
```

## License

MIT — see [LICENSE](LICENSE). The bundled game-design corpus (`catalog/corpus/`) carries its own per-source licenses (CC-BY, arXiv, free per-chapter); see `catalog/corpus/manifest.json`.

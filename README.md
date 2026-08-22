# 🗡️ EndlessDungeon

A single-player **soulslike roguelike** with unbounded AI-generated floors. A LangGraph "dungeon master" agent composes enemies, encounters, and narrative from your actions and character build — grounded in a game-design corpus, gated by four verification agents — while a deterministic Python engine owns all rules and combat.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Godot](https://img.shields.io/badge/Godot-4.7-478CBF?logo=godot-engine&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1.2-1C3C3C?logo=langchain&logoColor=white)
![LangSmith](https://img.shields.io/badge/LangSmith-traced-000000?logo=langchain&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-2E7D32)
![Status](https://img.shields.io/badge/status-Wave_6_%E2%80%94_hardened-2E7D32)

> **Status** — 🟢 **Wave 6 complete** (hardening: evals, latency budgets, anti-tamper, docs). See [`specs/`](specs/) for the spec-driven plan (`spec.md` → `plan.md` → `tasks.md`) and [`docs/`](docs/) for the living documentation.

> **Conventions used across these docs** — 🟠 critical rule/invariant · 🟢 success/goal/done · 🔴 problem/must-not/risk · 🔵 info

## Architecture (one line)

```
Godot 4.7 client (GDScript)  ⇄  FastAPI/WebSocket  ⇄  deterministic engine + LangGraph director + RAG (Qdrant)
```

> [!IMPORTANT]
> The engine owns **all** stats, combat, and enemy AI. The LLM only emits validated JSON content — it never writes mechanics.

Combat is real-time, **dice-free**, and deterministic: the client simulates, the server re-simulates the input log to verify — so a hacked client can't lie about results.

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
uv run docs-check
```

## Repository layout

```
server/   Python 3.12 (uv): FastAPI + LangGraph + Qdrant — engine, agent, RAG
client/   Godot 4.7.2 (GDScript): isometric renderer, NetworkManager, combat scenes
catalog/  content catalog + game-design corpus (see catalog/corpus/manifest.json)
docs/     living documentation (13 docs + Mermaid diagrams, docs-check drift gate)
specs/    spec-driven plan (spec.md → plan.md → tasks.md)
```

## Documentation index

| Doc | What |
|-----|------|
| [spec.md](specs/spec.md) | Requirements, invariants, acceptance criteria (WHAT) |
| [plan.md](specs/plan.md) | Architecture, tech stack, module design (HOW) |
| [tasks.md](specs/tasks.md) | Ordered execution roadmap |
| [01-gdd.md](docs/01-gdd.md) | Game design document (D2) |
| [02-architecture.md](docs/02-architecture.md) | System architecture (D1/D11) |
| [03-system-design.md](docs/03-system-design.md) | Authority model, single-write path |
| [04-game-states.md](docs/04-game-states.md) | State machines (D3/D7) |
| [05-protocol.md](docs/05-protocol.md) | WS protocol |
| [06-data-model.md](docs/06-data-model.md) | ERD |
| [07-agent-design.md](docs/07-agent-design.md) | Director + verifiers (D4/D9) |
| [08-content-catalog.md](docs/08-content-catalog.md) | Catalog + RAG + floors (D8/D10) |
| [09-ai-rag-corpus.md](docs/09-ai-rag-corpus.md) | Game-design corpus |
| [10-runbook.md](docs/10-runbook.md) | Ops |
| [11-evals.md](docs/11-evals.md) | Evals |
| [12-contributing.md](docs/12-contributing.md) | Contributing |
| [13-security.md](docs/13-security.md) | Threat model |
| [STYLE.md](docs/STYLE.md) | Doc style guide (enforced) |

## Contributing & docs style

All docs follow [`docs/STYLE.md`](docs/STYLE.md) — color-coded statement conventions (🟠 critical · 🟢 success · 🔴 problem · 🔵 info) + cross-references, enforced by `scripts/lint_docs.py` and the `docs-check` gate. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the PR workflow and [`AGENTS.md`](AGENTS.md) for agent instructions.

## License

MIT — see [LICENSE](LICENSE). The bundled game-design corpus (`catalog/corpus/`) carries its own per-source licenses (CC-BY, arXiv, free per-chapter); see `catalog/corpus/manifest.json`.

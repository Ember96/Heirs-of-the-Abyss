# EndlessDungeon — Agent Instructions

Guidance for AI agents and automated tooling working in this repository. Read `docs/STYLE.md` for the full documentation style guide — it is binding.

## Project in one line

A soulslike roguelike: Godot 4.7 isometric client ⇄ FastAPI/WebSocket ⇄ deterministic Python engine + LangGraph dungeon-master + RAG (Qdrant). The engine owns all stats/combat; the LLM only emits validated content.

## Documentation style — MANDATORY

Every Markdown file and Mermaid diagram **must** follow `docs/STYLE.md`. The four statement natures and their encoding are fixed:

| Nature | Color | Alert | Mermaid class |
|--------|-------|-------|---------------|
| Critical rule / invariant | 🟠 orange | `> [!WARNING]` / `> [!IMPORTANT]` | `crit` |
| Success / goal / done | 🟢 green | `> [!TIP]` | `ok` |
| Problem / must-not / risk | 🔴 red | `> [!CAUTION]` | `bad` |
| Info / context | 🔵 blue | `> [!NOTE]` | `info` |

**Before declaring any docs change complete, run:**

```bash
python3 scripts/lint_docs.py
```

A docs change that fails the lint is **not** done — fix it or don't commit it. Never invent a new color or alert type for these four natures. Every `docs/` + `specs/` file must also cross-reference related docs (a `## See also` section) — the lint enforces this too.

## Commit rules

- One todo = one atomic commit; conventional format: `feat|fix|test|docs|chore|perf(scope): message`; scope ∈ `server|agent|rag|sim|corpus|client|catalog|evals|security|docs`.
- Any commit touching `server/app`, `client/`, or `catalog/` must include its doc updates (the `docs:check` gate enforces this from T1.6).
- Never commit: `.env`, `data/`, `client/.godot/`, corpus binaries (only `catalog/corpus/manifest.json`), API keys.

## Critical invariants (never violate — see specs/spec.md §6)

1. The engine owns **all** stats, combat, and enemy AI; the LLM emits validated JSON + narrative only.
2. `commit_encounter` is the **single write path** into `Room.enemies[]`.
3. Combat is **dice-free** — pure function of (input log, seed, sim_version).
4. Typed gameplay actions **never** enter the LangGraph.
5. Every state-mutating LLM output passes the clamp layer **and** a verifier verdict.
6. No client-trusted value; no client save file; reconnect resumes the sim, never re-rolls it.

## Test discipline

- Server: `cd server && uv run pytest` — must stay green.
- Protocol/sim determinism contracts live in `server/tests/` and `sim_conformance.py`; no `random`/`randf()`/wall-clock timers in sim paths.
- Evidence for each todo under `docs/evidence/<todo-id>/`; self-report is never acceptance.

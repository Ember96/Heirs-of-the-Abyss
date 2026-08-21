# EndlessDungeon — Technical Plan (Spec-Driven Development)

Status: **Plan** — implements `spec.md`. Source of truth for HOW. Maps 1:1 to `tasks.md`.

## 1. Architecture

```
Godot 4.7 client (GDScript)          Python 3.12 server (FastAPI + uv)
├── NetworkManager (WebSocketPeer)   ├── WS gateway (auth, seq, HMAC, rate-limit, generation tracker)
├── sim_core.gd (deterministic)      ├── Deterministic engine (rules, floorgen, sim core in Python)
├── isometric render (TileMapLayer)  ├── LangGraph director (engine-first routing, interrupts)
└── combat scenes (hitbox=feedback)  ├── Tools (commit_encounter = single write path)
                                      ├── RAG (Qdrant hybrid: catalog + game-design corpus)
                                      └── Verifiers (Balance/Rules/Lore/Progression)
                                              │
                              SQLite (WAL, aiosqlite) + LangGraph checkpointer
                                              │
                              LangSmith (tracing + evals)   Qdrant (docker compose)
```

**Authority model**: engine owns all state/combat/AI; LLM emits validated JSON variants + narrative. `commit_encounter` is the single mutator of `Room.enemies[]`.

**Combat authority**: Option A (client-sim + server re-sim of tick-stamped input log) with B-ready protocol (`fight_snapshot` frame + shared sim core). Flip to B = deployment + client-render change only.

## 2. Tech stack (pinned)

| Layer | Choice | Version |
|-------|--------|---------|
| Server | Python | 3.12 |
| Package | uv | 0.11.x |
| Web | FastAPI + uvicorn + websockets | latest |
| Agent | langgraph | 1.2.x |
| Checkpoint | langgraph-checkpoint-sqlite | 3.1.x |
| Models | langchain-openai / langchain-anthropic / Ollama (config-driven) | latest |
| Vector | qdrant-client (Qdrant via docker compose) | latest |
| Validation | pydantic | ≥2.9 |
| Tracing | langsmith | latest |
| Client | Godot | 4.7.2 |
| Scripting | GDScript | — |

## 3. Repository layout (monorepo)

```
server/
  app/
    main.py              # FastAPI + WS /game endpoint
    game/
      models.py           # Pydantic: Player, Floor, Room, Enemy, FightState, GameSession…
      rules.py            # combat sim spec + engine rules
      sim/core.py         # deterministic sim core (Python)
      floorgen.py         # seeded 4-room floor generator
    agent/
      graph.py            # StateGraph: route_intent → floor/encounter/boss/narrate/flavor
      tools.py            # commit_encounter, get_player_build, save_lore_fact, …
      input_pipeline.py   # sanitization, injection guardrails, rate limits
      generator.py        # pre-gen, cache, token budget, termination
      verifiers.py        # 4 judges
    rag/
      indexer.py, retriever.py, composer.py
    persistence.py        # SQLite WAL + aiosqlite + single-writer lock
  scripts/
    mock_server.py, headless_player.py, sim_conformance.py, playtest.py
  tests/                  # test_protocol, test_e2e_socket, test_* per wave
client/
  project.godot, scripts/ (NetworkManager.gd, sim_core.gd), scenes/
catalog/                  # minimal/ (wave 2) → full MVP (wave 4); corpus/ (legal, provenance)
docs/                     # 01-gdd … 13-security (living docs)
specs/                    # spec.md, plan.md, tasks.md (this SDD)
```

## 4. Module design (key decisions)

- **Engine-first routing** (`graph.py` + WS handler): typed actions dispatch to engine functions directly; only free-form intents enter the graph. Keeps latency + cost budgets achievable (1–2 LLM calls/encounter).
- **Shared sim core** (`rules.py` spec + `sim/core.py` + `client/scripts/sim_core.gd`): pure `(state, inputs, seed) → (state, events)`, integer/fixed-point, fixed 60Hz tick, seeded Xorshift128+, no Godot physics in sim. Conformance corpus (≥2000 cases) proves byte-identical outputs.
- **`commit_encounter`** (`tools.py`): synchronous critical section (placement check + clamp + append, zero awaits) under a per-session engine lock; verdict-required (synthetic fallback verdict); only mutator of `Room.enemies[]`.
- **Verifier loop** (`verifiers.py`): `compose → clamp → 4 judges → commit`; judges gate committed content only; streamed narrative grounded structurally (typed facts), never judge-gated.
- **Generation lifecycle** (`generator.py` + WS handler): per-narrative `asyncio.timeout(GENERATION_TIMEOUT)` tracker; exactly one terminal frame on every path; pre-gen off critical path; cache key `(session_id, content_version, seed, floor_index, build_hash)`.
- **Protocol** (`docs/05-protocol.md` + `main.py`): envelope `{v,type,id,seq,payload,hmac}`; HMAC-SHA256 over `type|id|seq|payload`; per-frame id semantics; 64KB cap (state_sync multi-frame exempt); `fight_input_ack`, `fight_snapshot` (B-ready), `fight_submit` without full log.

## 5. Data model (Pydantic → SQLite)

`Player` (hp/atk/def/level/xp/gold/build_tags), `Inventory`, `Equipment`, `Floor` (seed, rooms[]), `Room` (type, enemies[]), `Enemy` (parts/affixes/stats/behavior_table), `FightState`, `BossSkill`, `GameSession` (session_id, resume_token, terminal, learnt_boss_skills[]), `HometownState`, `ShrineState`, `MarketState`.

Tables: `sessions`, `pregen_cache`, `generated_lore`, `action_ids` (dedup, last 100) + LangGraph checkpoint tables. Retention: sessions 30d/100MB cascading to all stores; checkpoints last 50/thread.

## 6. Implementation phases (maps to tasks.md)

| Phase | Content | Exit |
|-------|---------|------|
| 1 Foundation | scaffold, protocol spec, WS gateway (HMAC/seq/rate-limit/tracker), Godot NetworkManager, e2e socket conformance, docs gate | hardened socket + docs gate green |
| 2 Core | models + seeded RNG, combat sim spec, dual sim core + conformance, floorgen, persistence + headless player | headless playable (AI off) |
| 3 Director | graph + checkpointer + mutex, tools (commit_encounter), input pipeline, generator, resume/retention, verifiers | full AI loop, verifier-gated |
| 4 RAG | catalog seed, Qdrant hybrid, composer + clamps, corpus ingestion, lore quarantine | retrieval + compose gates green |
| 5 Client | isometric render, sim-core wiring, real-time combat + fight-log validation, scenes, reconnect | human-playable soulslike loop |
| 6 Hardening | evals, latency/cost, anti-tamper verification, docs/quickstart/balance | all gates green |

## 7. Testing strategy

- **TDD** for rules engine + sim core (conformance corpus written first); tests-after for agent/RAG/client.
- **Per-todo agent-executable QA**: acceptance + happy/failure scenarios, evidence under `docs/evidence/<todo-id>/`.
- **Headless**: `pytest` (server), `godot --headless` (logic), `xvfb-run` + ffmpeg (visual), `docker compose up qdrant` (RAG).
- **Evals (LangSmith)**: recorded session corpus → datasets → gates (NFR-8).

## 8. Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| Real-time combat engineering surface | shared sim core + conformance corpus; no Godot physics in sim; tick-stamped protocol |
| LLM latency | combat LLM-free; pre-gen + cache; streaming; small-model routing |
| LLM balance drift | Pydantic schema + clamps + 4 verifier judges + bounded retry |
| Prompt injection | server-side sanitization; typed tool gates; lore quarantine; corpus-as-data |
| Store growth | retention + LRU + ring buffer + dedup bound across every store |
| Cost | prompt caching (~90% input cut); generated-content cache; 1–2 calls/encounter |

## 9. Godot MCP (tooling note)

Control the client via `@coding-solo/godot-mcp` (configured in `opencode.json`): `create_scene`, `add_node`, `load_sprite`, `save_scene`, `run_project`, `get_debug_output`, `launch_editor`, `list_projects`. Author `.gd`/`.tscn` with edit tools, verify with `run_project` + `get_debug_output`. (Richer alternative if live editor manipulation is needed: `@elfensky/godot-mcp`, 61 tools, requires the `addons/godot_mcp` plugin symlinked into `client/`.)

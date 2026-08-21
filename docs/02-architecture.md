# System architecture

> Status: **skeleton** — seeded in T1.1; full content lands across the waves (see `specs/tasks.md`). This file is covered by the `docs:check` drift gate.

System architecture (D1), deployment (local-first, docker compose for Qdrant), data flow, living-docs sync (D11)

## Diagrams

### D1 — System architecture

```mermaid
flowchart LR
  subgraph Client["Godot 4.7 client (GDScript)"]
    UI["UI / HUD / narrative log"]
    Net["NetworkManager (WebSocketPeer autoload)"]
    Sim["Real-time combat sim (deterministic, client-side)"]
    Render["Isometric tile renderer + Y-sort"]
    UI <--> Net
    UI <--> Sim
    Sim <--> Render
  end
  Net <-->|"JSON frames (v1 protocol)"| WS["FastAPI / WebSocket server"]
  WS --> H["WS handler: auth, serialization, busy, generation tracker, 30s termination"]
  H --> E["Deterministic rules engine (server/app/game)"]
  E --> DB[("SQLite — WAL, aiosqlite, single-writer lock")]
  H --> G["LangGraph dungeon-director (engine-first routing)"]
  G --> T["Engine-gateway tools: commit_encounter, get_player_build, get_fight_facts, save_lore_fact"]
  G --> R["RAG composer (Qdrant hybrid: dense + BM25 + payload filters)"]
  R --> CAT[("Content catalog: parts, affixes, items, themes, lore")]
  G --> LLM["Hosted LLM — OpenAI / Anthropic / Ollama (config-driven)"]
  G -.-> LS["LangSmith: tracing, evals, feedback"]
  H -.-> LS
  E --> V["Verification agents: balance, rules, lore, progression"]
  V --> G
```

### D11 — Living-docs sync (constantly updated)

```mermaid
flowchart LR
  A["docs/ (Mermaid + Markdown)"] --> B["Product code (server/app, client, catalog)"]
  B --> C["uv run docs:check (regenerate from source + diff)"]
  C --> D{"Docs match code?"}
  D -->|yes| E["commit"]
  D -->|no| F["regenerate diagrams / fix drift (fail the gate)"]
  F --> A
```

<!-- content to follow -->
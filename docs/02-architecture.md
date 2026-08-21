# System architecture

> Status: **skeleton** — seeded in T1.1; full content lands across the waves (see `specs/tasks.md`). This file is covered by the `docs:check` drift gate.

System architecture (D1), deployment (local-first, docker compose for Qdrant), data flow, living-docs sync (D11)

> **Diagram legend** — 🟠 critical/gate · 🟢 success/verified · 🔴 drift/failure · 🔵 info

## Diagrams

### D1 — System architecture

```mermaid
flowchart LR
  classDef crit fill:#FFF3E0,stroke:#F57C00,stroke-width:2px,color:#E65100,font-weight:bold
  classDef ok   fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px,color:#1B5E20,font-weight:bold
  classDef info fill:#E3F2FD,stroke:#1565C0,stroke-width:2px,color:#0D47A1

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
  WS --> H["WS handler: auth, serialization, busy, generation tracker, 30s termination"]:::info
  H --> E["Deterministic rules engine (server/app/game) — OWNS all stats"]:::crit
  E --> DB[("SQLite — WAL, aiosqlite, single-writer lock")]
  H --> G["LangGraph dungeon-director (engine-first routing)"]
  G --> T["Engine-gateway tools: commit_encounter = SINGLE write path, get_player_build, get_fight_facts, save_lore_fact"]:::crit
  G --> R["RAG composer (Qdrant hybrid: dense + BM25 + payload filters)"]
  R --> CAT[("Content catalog: parts, affixes, items, themes, lore")]
  G --> LLM["Hosted LLM — OpenAI / Anthropic / Ollama (config-driven)"]
  G -.-> LS["LangSmith: tracing, evals, feedback"]
  H -.-> LS
  E --> V["Verification agents: balance, rules, lore, progression"]:::ok
  V --> G
```

### D11 — Living-docs sync (constantly updated)

```mermaid
flowchart LR
  classDef ok  fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px,color:#1B5E20,font-weight:bold
  classDef bad fill:#FFEBEE,stroke:#C62828,stroke-width:2px,color:#B71C1C

  A["docs/ (Mermaid + Markdown)"] --> B["Product code (server/app, client, catalog)"]
  B --> C["uv run docs:check (regenerate from source + diff)"]
  C --> D{"Docs match code?"}
  D -->|yes| E["commit"]:::ok
  D -->|no| F["regenerate diagrams / fix drift (fail the gate)"]:::bad
  F --> A
```

## See also

- [System design — authority model](03-system-design.md)
- [WS v1 protocol](05-protocol.md)
- [Agent design — director graph](07-agent-design.md)
- [Security — threat model](13-security.md)

<!-- content to follow -->

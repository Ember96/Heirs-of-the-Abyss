# Game Design Document

> Status: **skeleton** — seeded in T1.1; full content lands across the waves (see `specs/tasks.md`). This file is covered by the `docs:check` drift gate.

Vision, design pillars, core loop, player fantasy, scope (MVP: 3 classes, 10 enemies, 3 bosses), OUT list

> **Diagram legend** — 🟠 critical/gate · 🟢 checkpoint/reward · 🔴 terminal/failure · 🔵 info

## Diagrams

### D2 — Core game loop (macro)

```mermaid
flowchart TD
  classDef crit fill:#FFF3E0,stroke:#F57C00,stroke-width:2px,color:#E65100,font-weight:bold
  classDef ok   fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px,color:#1B5E20,font-weight:bold
  classDef bad  fill:#FFEBEE,stroke:#C62828,stroke-width:2px,color:#B71C1C
  classDef info fill:#E3F2FD,stroke:#1565C0,stroke-width:2px,color:#0D47A1

  A["HOMETOWN: banked inventory, descend"] --> B["Enter sector (5 floors)"]
  B --> C["Floor = 4 rooms: 3 enemy + 1 special"]
  C --> D{"Room type?"}
  D -->|enemy| E["Real-time soulslike fight (client sim)"]
  E --> F["Server re-simulates action log → validates result"]
  F --> G["Loot / XP / gold committed by engine"]
  D -->|loot| G
  D -->|shrine| H["Light bonfire (components) → checkpoint/rest"]:::ok
  D -->|market| I["Buy / restock (gold)"]
  D -->|event| J["Event (lore / hazard / reward)"]
  G --> K{"Boss floor?"}
  H --> K
  I --> K
  J --> K
  K -->|no| C
  K -->|yes| L["Boss fight (result-validated)"]:::crit
  L --> M["Unlock boss skill / characteristic (or next level)"]:::ok
  M --> N["Resting shrine = anchor: return home or descend deeper"]:::ok
  N --> A
  N --> B
```

## See also

- [Specification (goals + user stories)](../specs/spec.md#2-goals--non-goals)
- [System architecture (D1)](02-architecture.md)
- [Combat state machine (D7)](04-game-states.md)
- [Floor template & pacing (D10)](08-content-catalog.md)

<!-- content to follow -->

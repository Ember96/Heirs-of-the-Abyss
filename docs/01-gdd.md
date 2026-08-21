# Game Design Document

> Status: **skeleton** — seeded in T1.1; full content lands across the waves (see `specs/tasks.md`). This file is covered by the `docs:check` drift gate.

Vision, design pillars, core loop, player fantasy, scope (MVP: 3 classes, 10 enemies, 3 bosses), OUT list

## Diagrams

### D2 — Core game loop (macro)

```mermaid
flowchart TD
  A["HOMETOWN: banked inventory, descend"] --> B["Enter sector (5 floors)"]
  B --> C["Floor = 4 rooms: 3 enemy + 1 special"]
  C --> D{"Room type?"}
  D -->|enemy| E["Real-time soulslike fight (client sim)"]
  E --> F["Server re-simulates action log → validates result"]
  F --> G["Loot / XP / gold committed by engine"]
  D -->|loot| G
  D -->|shrine| H["Light bonfire (components) → checkpoint/rest"]
  D -->|market| I["Buy / restock (gold)"]
  D -->|event| J["Event (lore / hazard / reward)"]
  G --> K{"Boss floor?"}
  H --> K
  I --> K
  J --> K
  K -->|no| C
  K -->|yes| L["Boss fight (result-validated)"]
  L --> M["Unlock boss skill / characteristic (or next level)"]
  M --> N["Resting shrine = anchor: return home or descend deeper"]
  N --> A
  N --> B
```

<!-- content to follow -->
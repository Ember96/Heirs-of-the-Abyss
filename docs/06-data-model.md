# Data model

> Status: **skeleton** — seeded in T1.1; full content lands across the waves (see `specs/tasks.md`). This file is covered by the `docs-check` drift gate.

ERD (D6) generated from the Pydantic models

> **Diagram legend** — `erDiagram` does not support `classDef` coloring; `GAME_SESSION` is the **root aggregate** (every per-session store — `HOMETOWN_STATE`, `GENERATED_LORE`, `PREGEN_CACHE` — hangs off it and is purged with it, retention cascade). Regenerated from `server/app/game/models.py` by `docs-check`.

## Diagrams

### D6 — Data model (ERD, regenerated from Pydantic models)

```mermaid
erDiagram
  GAME_SESSION ||--|| PLAYER : owns
  GAME_SESSION ||--o| HOMETOWN_STATE : banks
  PLAYER ||--o| INVENTORY : carries
  PLAYER ||--o| EQUIPMENT : equips
  FLOOR ||--o{ ROOM : contains
  ROOM ||--o| ENCOUNTER : spawns
  ENCOUNTER ||--o| ENEMY : instantiates
  ENEMY }o--o{ CATALOG_PART : composed_of
  ENEMY }o--o{ AFFIX : applies
  CATALOG_ITEM ||--o| MARKET : stocked_in
  GAME_SESSION ||--o| GENERATED_LORE : quarantines
  GAME_SESSION ||--o| PREGEN_CACHE : caches
```

## Generated ERD (from models.py)

<!-- ERD-GENERATED-START -->

```mermaid
erDiagram
  BossSkill {
    string id
    string level
  }
  Enemy {
    string name
    string parts
    string affixes
    string stats
    string behavior_table
  }
  Equipment {
    string weapon
    string armor
    string accessory
  }
  FightState {
    string fight_id
    string seed
    string tick
    string player_state
    string enemy_states
  }
  Floor {
    string seed
    string floor_index
    string rooms
  }
  GameSession {
    string session_id
    string resume_token
    string seed
    string player
    string current_floor
    string sector
    string anchor_floor
    string run_state
    string terminal
    string learnt_boss_skills
    string shrine
    string market
    string hometown
  }
  HometownState {
    string banked_inventory
  }
  Inventory {
    string items
  }
  Item {
    string id
    string name
    string tags
    string stat_profile
  }
  MarketState {
    string stock
    string restock_tick
  }
  Player {
    string hp
    string max_hp
    string attack
    string defense
    string level
    string xp
    string gold
    string class_tag
    string equipment
    string build_tags
  }
  Room {
    string type
    string enemies
    string data
  }
  ShrineState {
    string lit
    string components_held
  }
```

<!-- ERD-GENERATED-END -->

## See also

- [System design — single-write path](03-system-design.md)
- [Game states — FightState](04-game-states.md)

<!-- content to follow -->

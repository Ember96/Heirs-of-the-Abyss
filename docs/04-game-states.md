# Game states

> Status: **skeleton** — seeded in T1.1; full content lands across the waves (see `specs/tasks.md`). This file is covered by the `docs-check` drift gate.

State machines: meta (D3), combat/soulslike (D7), floor lifecycle, room types

> **Diagram legend** — 🟠 critical/gate · 🟢 checkpoint/success · 🔴 terminal/failure · 🔵 info

## Diagrams

### D3 — Meta game-state machine (engine)

```mermaid
stateDiagram-v2
  classDef ok   fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px,color:#1B5E20,font-weight:bold
  classDef bad  fill:#FFEBEE,stroke:#C62828,stroke-width:2px,color:#B71C1C
  classDef info fill:#E3F2FD,stroke:#1565C0,color:#0D47A1

  [*] --> HOMETOWN
  HOMETOWN --> FLOOR: descend (from anchor)
  FLOOR --> COMBAT: enter enemy/boss room
  COMBAT --> FLOOR: result validated
  FLOOR --> MARKET: enter market room
  MARKET --> FLOOR: leave
  FLOOR --> SHRINE: enter shrine
  SHRINE --> FLOOR: rest / light bonfire
  FLOOR --> EVENT: enter event room
  EVENT --> FLOOR: resolve
  SHRINE --> HOMETOWN: return_home (keep inventory)
  COMBAT --> GAMEOVER: hp <= 0 (session terminal)
  GAMEOVER --> [*]
  class SHRINE ok
  class MARKET ok
  class GAMEOVER bad
```

### D7 — Soulslike combat state machine (deterministic, client sim + server validate)

```mermaid
stateDiagram-v2
  classDef crit fill:#FFF3E0,stroke:#F57C00,stroke-width:2px,color:#E65100,font-weight:bold
  classDef ok   fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px,color:#1B5E20,font-weight:bold

  [*] --> IDLE
  IDLE --> ROLLING: roll (i-frames)
  ROLLING --> IDLE: recovery
  IDLE --> GUARDING: hold shield stance
  GUARDING --> PARRYING: parry (timed window)
  PARRYING --> RIPOSTE: parry success -> posture break
  IDLE --> ATTACKING: attack (input buffered)
  ATTACKING --> IDLE: recovery
  GUARDING --> STAGGERED: posture broken (fatigue)
  IDLE --> STAGGERED: posture 0 (stun)
  STAGGERED --> IDLE: recover
  RIPOSTE --> IDLE: riposte ends
  note right of IDLE: stamina gates every action; regen while IDLE; parry/riposte and posture are seeded-deterministic for replay
  class STAGGERED crit
  class RIPOSTE ok
```

## See also

- [System architecture (engine)](02-architecture.md)
- [WS protocol — fight frames](05-protocol.md)
- [Data model — FightState](06-data-model.md)

<!-- content to follow -->

# Agent design

> Status: **complete** — LangGraph director graph (D4), tool layer, verification-agent loop (D9), LLM wired via OpenRouter.

> [!NOTE]
> The director's LLM calls route through `app/llm.py` (OpenRouter, OpenAI-compatible): `MODEL_FAST` (8B) for routing/judges, `MODEL_CHAT` (70B) for composition and narrative. The LLM only emits content — `enemy_id` + affixes — and the engine supplies stats from the catalog; every variant passes clamp + the four judges before `commit_encounter`.

LangGraph director graph (D4), tool layer, verification-agent loop (D9)

> **Diagram legend** — 🟠 critical/gate · 🟢 pass/success · 🔴 fail/fallback · 🔵 info

## Diagrams

### D4 — LangGraph dungeon-director graph

```mermaid
flowchart TD
  classDef crit fill:#FFF3E0,stroke:#F57C00,stroke-width:2px,color:#E65100,font-weight:bold
  classDef ok   fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px,color:#1B5E20,font-weight:bold
  classDef bad  fill:#FFEBEE,stroke:#C62828,stroke-width:2px,color:#B71C1C
  classDef info fill:#E3F2FD,stroke:#1565C0,stroke-width:2px,color:#0D47A1

  RI{"route_intent"} -->|encounter| EG["encounter_gen"]
  RI -->|talk| NA["narrate"]
  RI -->|flavor| FL["flavor"]

  subgraph gen ["encounter pipeline"]
    EG --> CV["compose_variant"]
    CV --> VA["4 verification judges"]:::ok
    VA -->|pass| CE["commit_encounter"]:::crit
    VA -->|fail| FB["retry ≤2"]:::bad
    FB -->|exhausted| WD["interrupt: fallback / flee"]
  end

  subgraph narr ["narration"]
    NA --> TXT["narrative prose"]
  end

  CE --> CACHE["pre-gen cache"]
  FL --> NA

  WD -.->|resume| FB
  CACHE -.-> N1["typed actions NEVER enter the graph"]:::info
```

### D9 — Verification-agent loop

```mermaid
flowchart TD
  classDef ok  fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px,color:#1B5E20,font-weight:bold
  classDef bad fill:#FFEBEE,stroke:#C62828,stroke-width:2px,color:#B71C1C
  classDef info fill:#E3F2FD,stroke:#1565C0,color:#0D47A1

  A["Main agent output"] --> B["Balance Judge"]
  A --> C["Rules Judge"]
  A --> D["Lore Consistency"]
  A --> E["Progression Auditor"]
  B --> F{"all pass?"}:::info
  C --> F
  D --> F
  E --> F
  F -->|yes| G["Commit to engine"]:::ok
  F -->|no| H["Repair prompt → retry → fallback"]:::bad
```

## See also

- [WS protocol — decision frames](05-protocol.md)
- [Content catalog — compose pipeline](08-content-catalog.md)
- [System design — commit_encounter](03-system-design.md)


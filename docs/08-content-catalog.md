# Content catalog

> Status: **complete** — catalog schema, RAG retrieval, variant composition + clamps, floor template & pacing (D10), token budget, content pipeline (D8).

Catalog schema, RAG retrieval, variant composition + clamps, floor template & pacing (D10), token budget, content pipeline (D8)

> **Diagram legend** — 🟠 critical/gate · 🟢 pass/success · 🔴 fail/fallback · 🔵 info

## Diagrams

### D8 — Content pipeline: pre-gen → compose → clamp → verify → commit

```mermaid
flowchart LR
  classDef crit fill:#FFF3E0,stroke:#F57C00,stroke-width:2px,color:#E65100,font-weight:bold
  classDef ok   fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px,color:#1B5E20,font-weight:bold
  classDef bad  fill:#FFEBEE,stroke:#C62828,stroke-width:2px,color:#B71C1C
  classDef info fill:#E3F2FD,stroke:#1565C0,stroke-width:2px,color:#0D47A1

  A["Sector entry / floor progress"] --> B["Pre-gen background task (asyncio, async LLM, token-capped)"]
  B --> C["RAG retrieval (hybrid: dense + BM25, payload filters on build weakness)"]
  C --> D["compose_variant (Pydantic schema, ToolStrategy retry <=2)"]
  D --> E["Deterministic clamp layer (budget ±25%, ids verified, derived stats recomputed)"]:::info
  E --> F["Verification agents (balance/rules/lore/progression)"]:::ok
  F -->|pass| G["commit_encounter (atomic, placement-validated, single write path)"]:::crit
  F -->|fail| H["fallback (engine-standard) + generation_failed"]:::bad
  G --> I["Cache: (session_id, content_version, seed, floor_index, build_hash) LRU + TTL"]
```

### D10 — Floor template & pacing (token budget constraint)

```mermaid
flowchart TD
  classDef crit fill:#FFF3E0,stroke:#F57C00,stroke-width:2px,color:#E65100,font-weight:bold
  classDef ok   fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px,color:#1B5E20,font-weight:bold
  classDef info fill:#E3F2FD,stroke:#1565C0,stroke-width:2px,color:#0D47A1

  T["Floor template (deterministic, schema-capped JSON, fixed token budget)"] --> R1["Room 1: enemy"]
  T --> R2["Room 2: enemy"]
  T --> R3["Room 3: enemy"]
  T --> R4["Room 4: SPECIAL from layer-state pool"]
  R4 --> P{"Layer state rules"}
  P -->|early sector| A["loot / event likely"]:::info
  P -->|floor 1 of every sector| B["shrine (guaranteed checkpoint)"]:::ok
  P -->|"sector end (floor 5)"| C["boss room mandatory"]:::crit
  P -->|player low HP / struggling| D["tilt: easier event or shrine (anti-punish)"]:::ok
  P -->|player dominant| E["raise: harder encounter (anti-spoil)"]:::info
  T -.-> N1["budget per floor gen · 1 floor = 4 rooms · special room by layer state · band by auditor"]:::info
```

## Retrieval scale-out path

> [!NOTE]
> Retrieval runs **local single-process**: Cohere dense embeddings + BM25, fused with RRF, filtered by payload. Document vectors are cached in memory per catalog version.

> [!TIP]
> Flip to Qdrant (docker compose) when any of these hold: the corpus outgrows comfortable memory (~10k+ records), vectors must persist across restarts, or multiple server processes need shared search. The seam is `Retriever.retrieve()` — swap its body for a Qdrant query; BM25 stays as the fallback half.

## See also

- [AI RAG corpus — sources & licensing](09-ai-rag-corpus.md)
- [Agent design — verifier loop](07-agent-design.md)
- [Specification — FR-3 / FR-6](../specs/spec.md#4-functional-requirements)


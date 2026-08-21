# EndlessDungeon — Specification (Spec-Driven Development)

Status: **Spec** (this document is the source of truth for WHAT to build; `plan.md` = HOW, `tasks.md` = execution order). Supersedes the prose work plan in `.omo/plans/endless-dungeon.md`, which remains the design rationale record.

> **Legend** — 🟠 critical rule / invariant · 🟢 success / goal · 🔴 problem / must-not · 🔵 info / context

## 1. Purpose

A single-player **soulslike roguelike** with unbounded procedural floors. A LangGraph "dungeon master" agent composes content (enemies, encounters, narrative, floor themes) from a typed parts catalog, grounded in a game-design corpus, in response to the player's actions and character build — gated by verification agents before it ever touches game state.

> [!IMPORTANT]
> A deterministic rules engine owns all stats and combat. The LLM never does.

## 2. Goals & non-goals

### 🟢 Goals (MVP)

| Id | Goal |
|----|------|
| **G1** | Playable soulslike loop: hometown → descend a sector (5 floors) → real-time isometric combat → loot/market/shrine → boss → unlock a boss skill → return home → descend deeper |
| **G2** | Deterministic, dice-free combat: outcomes are pure functions of inputs + seed; a hacked/modded client cannot report a false result |
| **G3** | AI-director content: floors/encounters/narrative generated from player actions/build, within token budgets, verified by 4 judges before commit |
| **G4** | Grounded, safe GM: narrative references only engine facts; player text and corpus content cannot inject into the model |
| **G5** | Resilient: crash-resume restores exact state; every store bounded; generation always terminates |
| **G6** | Hardened + shareable: WSS+HMAC+strict schemas+rate limits; 13-doc package + diagrams; `docs:check` gate |

### 🔴 Non-goals (explicit)

> [!CAUTION]
> **Must NOT build** — these are hard exclusions, re-verified by F4 (scope fidelity).

- ❌ No generated art/audio/textures/fonts/models (content composed from catalog data, never file generation).
- ❌ No multiplayer, no leaderboards, no PvP anti-cheat, no screen recording.
- ❌ No offline mode (the game is a service; the client ships nothing of value).
- ❌ No dice/RNG in combat resolution; no client-trusted values; no client save files.
- ❌ No 3D; no real-time *networked* combat authority (Option A now, B-ready).

## 3. User stories

- **US1** As a player, I descend into a sector and fight through 4-room floors in real time (roll/block/parry/riposte with stamina and posture) without any random whiff.
- **US2** As a player, when I defeat a boss I unlock a boss skill (dash, +HP, +def, burning hits, loot chance) — or level it up if I already own it.
- **US3** As a player, I light a shrine (bonfire) with components I find, which lets me rest and return home, keeping my inventory.
- **US4** As a player, I buy/restock items at a market with gold.
- **US5** As a player, the dungeon adapts to my build — the AI composes enemies that probe my weaknesses, but never produces something unwinnable or trivially free.
- **US6** As a player, if I disconnect or crash mid-fight, I reconnect and resume the same fight deterministically.
- **US7** As a developer, I run `docs:check` and it fails any code change that didn't update its docs.

## 4. Functional requirements

### FR-1 Combat (deterministic soulslike sim)

- **FR-1.1** Real-time at a fixed **60 Hz** tick; outcomes are a pure function `(state, inputs, seed) → (state, events)`.
- **FR-1.2** Mechanics: roll (13 i-frames), guard, parry (12 active frames, 10-frame startup), riposte (×2), backstab (×1.5), posture break → stagger (×1.5), stamina (100; roll 18 / attack 22 / block 5 / regen 27/s idle).
- **FR-1.3** Damage = `max(1, atk − def)` × deterministic mechanical multipliers.

> [!WARNING]
> **No hit-chance rolls, no damage variance, no RNG crits.** Crits are mechanical (riposte/backstab/staggered), never random.

- **FR-1.4** Enemy AI = seeded behavior tables (deterministic given the seed); never wall-clock.
- **FR-1.5** Fight-length bound: **10 min / 36,000 ticks** → forced flee-resolution (reset, no rewards).

> ✅ **Acceptance**: dual GDScript/Python sim cores produce byte-identical state on a ≥2000-case conformance corpus; a tampered input log is rejected by server re-simulation.

### FR-2 Combat validation (Option A, B-ready)

- **FR-2.1** Client streams `fight_input` per tick (batched, acked via `fight_input_ack`); server appends **idempotently** and re-sims the merged log on `fight_submit`.
- **FR-2.2** `fight_submit` = `{fight_id, claimed_result, state_hash, sim_version}` (no full log — server already holds it).
- **FR-2.3** `verified:false` → re-attempts **capped ≤2**, then flee-resolution; repeated failures recorded in the telemetry hook.
- **FR-2.4** Server persists each acked batch (incremental prefix) so network drop, client crash, or server restart all resume the fight deterministically.

> ✅ **Acceptance**: scripted fight → `verified:true`; tampered claim → `verified:false`, no rewards, state unchanged; >64KB-equivalent log submits without `frame_too_large`.

### FR-3 Dungeon structure

- **FR-3.1** Sector = 5 floors (4 normal + 1 boss); one-way descent; boss must fall to reach the shrine.
- **FR-3.2** Floor = 4 rooms (3 enemy + 1 special): loot / event / market / shrine / boss.
- **FR-3.3** Shrine is **floor 1 of every sector** (guaranteed checkpoint), excluded from the floors 2–4 pool; ≥1 loot/event room guaranteed per sector (component source).
- **FR-3.4** Difficulty band = floor budget ±25% (never cheap-death, never spoiling).

> ✅ **Acceptance**: same seed → byte-identical floor; 1000-seed invariant test proves boss+shrine+loot/event guarantees hold.

### FR-4 Progression

- **FR-4.1** Death = permadeath (`game_over` → session `terminal`); shrine is a return anchor, not a respawn.
- **FR-4.2** `return_home` keeps banked inventory; re-enter resumes at the anchor.
- **FR-4.3** Boss defeat unlocks a boss skill or +1 level; market buys/restocks with gold.

> ✅ **Acceptance**: full headless run (via `headless_player.py`) lights a shrine, shops, returns home, levels a skill.

### FR-5 AI director (LangGraph)

- **FR-5.1** Engine-first routing: typed actions (`move/attack/use_item/rest/return_home/descend/run/shop/equip/drop`) are dispatched directly to the engine and **never enter the graph**; only `talk`/flavor/`decision` go through the graph.
- **FR-5.2** Content flows `compose → clamp → verify (4 judges) → commit_encounter` (single write path).
- **FR-5.3** Four judges — Balance, Rules, Lore Consistency, Progression Auditor — gate **committed content only**; streamed narrative is structurally grounded (typed `CombatFacts`/`FloorFacts`), not judge-gated.
- **FR-5.4** Every generation terminates with exactly one terminal frame within `GENERATION_TIMEOUT` (30s default).

> ✅ **Acceptance**: a deliberately unbalanced variant is rejected before commit; a hung generation yields `generation_failed` + fallback, game continues.

### FR-6 RAG content

- **FR-6.1** Typed catalog (≥60 parts, ≥30 affixes, ≥40 items, ≥10 themes, ≥30 lore; 3 classes, 10 enemies, 3 bosses).
- **FR-6.2** Qdrant hybrid retrieval (dense + BM25 + payload filters); recall@5 ≥70% on a golden set.
- **FR-6.3** Retrieval context capped at **≤1.5k tokens per call** (compose AND narrate); corpus + generated lore are wrapped as **untrusted data**.

> ✅ **Acceptance**: ≥95% schema-valid variants, 100% clamp-enforced, 0 unknown ids, ≤2 LLM calls per compose.

### FR-7 Protocol (hardened WS)

- **FR-7.1** Envelope `{v:1, type, id, seq, payload, hmac?}`; monotonic `seq` both directions; HMAC-SHA256 over `type|id|seq|payload`; 64KB frame cap (state_sync exempt, multi-frame).
- **FR-7.2** Per-frame `id` semantics pinned (action_id / narrative_id / fight_id / decision_id / session_id).
- **FR-7.3** Resume order pinned: `state_sync` first, then queued actions, then `narrative_replay` only if a stream was cut.

> ✅ **Acceptance**: forged hmac / replayed seq / oversized frame all rejected with typed errors, connection stays open.

## 5. Non-functional requirements

| Id | Requirement | Threshold |
|----|-------------|-----------|
| NFR-1 | Determinism | GDScript ≡ Python byte-identical on conformance corpus; zero module-level `random`/`randf()`/wall-clock in sim |
| NFR-2 | Latency (local) | turn p50 <3s, p95 <8s (combat turns LLM-free); streaming TTFT <1.5s; WS round-trip <100ms; fight re-sim <1s |
| NFR-3 | Single-write invariant | `commit_encounter` is the only mutator of `Room.enemies[]` (grep + mutation-proven) |
| NFR-4 | Verifier gate | verdict-required on `commit_encounter` (synthetic fallback verdict for engine-standard content) |
| NFR-5 | Security | WSS+HMAC+strict `extra="forbid"`+rate limits; no client-side content of value; server-side sanitization |
| NFR-6 | Bounded stores | sessions (30d/100MB), checkpoints (last 50/thread), cache (LRU+TTL), lore (ring 500), dedup (last 100) |
| NFR-7 | Docs | `uv run docs:check` green every wave; code→doc manifest with inverse check (unlisted file = fail; empty doc mapping = fail) |
| NFR-8 | Eval gates | rule-adherence ≥95%, schema-valid ≥95%, balance 100%, pacing-band 100%, verifier catch-rate ≥95%, narrative-quality ≥80% |

## 6. Invariants (must hold, verified by tests)

> [!WARNING]
> **Critical rules** — a violation is a defect, never a trade-off.

1. 🟠 The engine owns **all** stats, combat, and enemy AI. The LLM emits validated JSON variants + narrative only.
2. 🟠 `commit_encounter` is the **single write path**; it is a synchronous critical section (zero awaits) under a per-session engine lock.
3. 🟠 Combat is **dice-free**: a fight outcome is a pure function of (input log, seed, sim_version).
4. 🟠 Typed gameplay actions **never** enter the LangGraph.
5. 🟠 Every LLM output that mutates state passes the clamp layer **and** a verifier verdict.
6. 🟠 No client-trusted value; no client save file; reconnect resumes the deterministic sim, never re-rolls it.

## 7. Edge cases (each must have a test)

> [!NOTE]
> Death mid-fight → flee/reset semantics (not free restart). Client crash / server restart mid-fight → deterministic resume. Desync (`verified:false`) → capped re-attempts → flee. Generation hang → timeout + fallback + terminal frame. Out-of-context `decision` → `busy`/`rule_violation`. Resume from pruned session → `session_not_found` + new-game. Illegal `descend` before boss → `rule_violation`. Corpus/license gate rejects NC/SA sources.

## 8. Out of scope

> [!CAUTION]
> Multiplayer, leaderboards, PvP, screen recording, offline mode, generated assets, 3D, real-time networked combat (Option B), per-account auth (dev token only), CI beyond lint+test, scaling beyond local + docker-compose Qdrant.

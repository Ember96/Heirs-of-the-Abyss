# Heirs of the Abyss — Tasks (Spec-Driven Development)

Status: **Tasks** — executable, dependency-ordered list implementing `plan.md`. Each task = one atomic commit (conventional commits). Acceptance criteria reference `spec.md` (FR/NFR/invariants) and require evidence under `docs/evidence/<task-id>/`.

> **Legend** — ✅ done · ⏳ pending · 🟢 done-claim (TIP) · 🔴 final gate (CAUTION, all must APPROVE)

Dependencies are strictly ordered within a wave; each wave's **done-claim** gates the next wave.

---

## 🏗️ Wave 1 — Foundation (depends: none)

- ✅ **T1.1 Repo scaffold + tooling** — `git init`; `server/` (uv pyproject, pinned deps), `client/` (Godot 4.7.2 project), `catalog/`, `docs/` (seed from design-docs blueprint), `README.md`, `LICENSE` (MIT), `.env.example`, `.gitignore`.
  - Deps: — · Accept: `uv run python -c "import fastapi, langgraph, qdrant_client, pydantic"` green; Godot opens project.
- ✅ **T1.2 WS protocol spec v1** — `docs/05-protocol.md` exhaustive + `server/app/protocol.py` (envelope + 23 payload schemas + HMAC + SeqTracker); all message types, per-frame `id` semantics, resume order, idempotency, error codes.
  - Deps: T1.1 · Accept: `test_protocol.py` (42 tests) validates example frames (HMAC, seq, resume, 64KB cap) — satisfies FR-7.
- ✅ **T1.3 FastAPI server skeleton + generation tracker + auth** — `/health`, WS `/game` with registry, per-session `asyncio.timeout(GENERATION_TIMEOUT)` tracker, HMAC verify, rate limits, dev-token `hello`, `mock_server.py`, LangSmith init.
  - Deps: T1.2 · Accept: handshake + HMAC round-trip; bad token/hmac rejected with typed error.
- ✅ **T1.4 Godot skeleton + NetworkManager** — autoload WebSocketPeer (connect/poll/HMAC/seq/heartbeat/reconnect/resume); signals; bootstrap scene.
  - Deps: T1.2 · Accept: connects to `mock_server.py`, auth+HMAC, reconnect+resume (evidence via xvfb + ffmpeg).
- ✅ **T1.5 E2E socket conformance** — round-trip <100ms; double-action order; generation-lifecycle terminal frame; resume ordering; out-of-context decision.
  - Deps: T1.3, T1.4 · Accept: all conformance cases headless.
- ✅ **T1.6 Living-docs scaffold + drift gate** — materialize `docs/`; `uv run docs-check` (regenerate derivable docs + diff, exit non-zero on drift); code→doc manifest with inverse check.
  - Deps: T1.1 · Accept: gate green on clean tree; deliberate drift fails naming the file — satisfies NFR-7.

> [!TIP]
> **Wave 1 done-claim** — `pytest test_protocol.py test_e2e_socket.py` green; `docs-check` green; headless Godot logs `SESSION_READY`.

## ⚙️ Wave 2 — Deterministic core (depends: Wave 1)

- ✅ **T2.1 Game-state models + seeded RNG** — Pydantic models (`Player/Floor/Room/Enemy/FightState/GameSession/…`); `SeededRandom` (Xorshift128+); per-fight RNG isolation; `build_tags` recompute on equip.
  - Deps: T1.1 · Accept: determinism across processes; zero module-level `random`.
- ✅ **T2.2 Combat sim spec + engine rules** — `rules.py` + `catalog/minimal/` seed; damage `max(1, atk−def)` × mechanical multipliers; pinned stamina/posture/i-frame/parry values; fight-length bound; sector/shrine/death/market/boss-skill rules.
  - Deps: T2.1 · Accept: unit tests (frame-exact windows, behavior-table determinism, descent invariants) — satisfies FR-1, FR-3, FR-4.
- ✅ **T2.3 Shared sim core (dual impl + conformance)** — `sim/core.py` + `sim_core.gd`; `sim_conformance.py` ≥2000 seeded cases, byte-identical.
  - Deps: T2.2 · Accept: corpus green both languages — satisfies NFR-1, FR-2.
- ✅ **T2.4 Seeded floor generator** — 4-room template; shrine floor-1 guaranteed + excluded from 2–4 pool; ≥1 loot/event per sector; difficulty band ±25%; `place_enemy`; token caps.
  - Deps: T2.2 · Accept: 1000-seed invariants; reachability; `place_enemy` sole append path.
- ✅ **T2.5 Persistence + session service + retention** — SQLite WAL/aiosqlite/single-writer; tables; retention cascade; `headless_player.py`.
  - Deps: T2.1, T2.4 · Accept: save/load round-trip; retention removes all rows across stores.

> [!TIP]
> **Wave 2 done-claim** — `headless_player.py` walks a floor, fights via sim, lights shrine, shops, returns home, levels a skill; `sim_conformance.py` green.

## 🧠 Wave 3 — Director (depends: Wave 2)

- ✅ **T3.1 Agent graph + checkpointer + concurrency** — StateGraph, `interrupt()`, checkpointer; engine-first routing; graph mutex; `RemoveMessage` trim; narrate grounded in typed facts.
  - Deps: T2.5 · Accept: interrupt/resume no re-bill; `talk` during narration → busy — satisfies FR-5.1, FR-5.4.
- ✅ **T3.2 Tool layer (engine gateway)** — `commit_encounter` (single write path, synchronous critical section, verdict-required); other tools (provenance forcing, call cap); no `roll_dice`.
  - Deps: T2.4 · Accept: mutation + race tests prove sole-mutator — satisfies NFR-3, NFR-4.
- ✅ **T3.3 Input pipeline + sanitization** — length/type limits, instruction/data separation, audit log, moderation hook, rate limits.
  - Deps: T3.1 · Accept: injection string can't alter system prompt; over-long → `input_too_long`.
- ✅ **T3.4 Content generation pipeline** — pre-gen off critical path; cache key + LRU + TTL; cold-cache fallback; token-budget; terminal frame.
  - Deps: T3.1 · Accept: cache-hit descent; hung gen → `generation_failed` + fallback — satisfies FR-5.4.
- ✅ **T3.5 Session resume + retention + queue ownership** — resume → `state_sync` first → queued actions → `narrative_replay`; checkpoint prune.
  - Deps: T3.1, T2.5 · Accept: crash-resume exact state; no double-apply — satisfies FR-2.4, NFR-6.
- ✅ **T3.6 Verification-agent loop** — 4 judges gate committed content only; bounded repair ≤2 → fallback; verdicts traced.
  - Deps: T3.2 · Accept: unbalanced variant rejected before commit — satisfies FR-5.3, NFR-4.

> [!TIP]
> **Wave 3 done-claim** — full AI loop (action → route → pre-gen → verify → commit → narrate → decision → resume); generation always terminates; `docs-check` green.

## 📚 Wave 4 — RAG (depends: Wave 3; T4.3 replaces T3.2 stub)

- ✅ **T4.1 Catalog seed data** — full MVP catalog (3 classes/10 enemies/3 bosses/boss skills/market stock).
  - Deps: T2.2 · Accept: referential integrity, counts ≥ targets — satisfies FR-6.1.
- ✅ **T4.2 Qdrant + hybrid retrieval** — docker-compose; indexer; retriever (dense+BM25+RRF+payload filters); golden set (20).
  - Deps: T4.1 · Accept: recall@5 ≥70% — satisfies FR-6.2.
- ✅ **T4.3 Variant composition + clamp layer** — `compose_variant` (retrieval ≤1.5k → LLM → clamp); commit via `commit_encounter`.
  - Deps: T4.2, T3.2 · Accept: ≥95% schema-valid, 100% clamp-enforced, ≤2 calls — satisfies FR-6.3, FR-5.2.
- ✅ **T4.4 Game-design corpus ingestion** — FREE-LEGAL set with license+provenance; license gate (redistribution AND MIT-compat); corpus-as-untrusted-data.
  - Deps: T4.2 · Accept: every record has license/source/domain; hostile-corpus injection blocked — satisfies FR-6.3, NFR-5.
- ✅ **T4.5 Safety: lore quarantine + moderation** — ring buffer 500/session; provenance honored on re-embed.
  - Deps: T3.2, T4.2 · Accept: store bound; no cross-session leakage.

> [!TIP]
> **Wave 4 done-claim** — catalog+corpus indexed with provenance; compose always schema-valid + clamp + verifier passing; lore bounded/quarantined.

## 🗡️ Wave 5 — Client (depends: Wave 2 protocol + mock; Wave 3/4 content optional)

- ✅ **T5.1 Isometric rendering** — TileMapLayer `TILE_SHAPE_ISOMETRIC` + separate layers + Y-sort; screen↔iso; placeholder shapes.
  - Deps: T1.4 · Accept: same seed → identical rendered floor (xvfb screenshot diff).
- ✅ **T5.2 GDScript sim core mirror + conformance re-run** — wire `sim_core.gd`; re-run conformance in-engine.
  - Deps: T2.3, T5.1 · Accept: corpus green with in-engine GDScript.
- ✅ **T5.3 Real-time combat** — hitbox/hurtbox feedback-only; sim-computed hits; input buffering; fight-log streaming; `verified:false` cap ≤2; reconnect/crash resume.
  - Deps: T5.2 · Accept: scripted fight → `verified:true`; tampered log → `verified:false` — satisfies FR-2.
- ✅ **T5.4 Game scenes** — hometown/market/shrine/boss/loot/event; inventory+equipment; combat HUD; game-over; escaped narrative log.
  - Deps: T5.3 · Accept: full scene flow against mock server.
- ✅ **T5.5 Reconnection + error handling** — reconnect overlay; `state_sync` wholesale replace; error toasts; fight-mid-flight resume.
  - Deps: T5.3, T1.5 · Accept: kill/restart server mid-fight → same fight state.

> [!TIP]
> **Wave 5 done-claim** — human-playable loop against the real server; `fight_result verified:true` in logs; `docs-check` green.

## 🛡️ Wave 6 — Hardening (depends: Wave 5)

- ✅ **T6.1 LangSmith eval suite** — record corpus via scripted sessions; datasets; code evaluators; thresholds (NFR-8).
  - Deps: Wave 3–5 · Accept: eval run produces report; seeded regression fails balance gate.
- ✅ **T6.2 Latency + cost verification** — `playtest.py` measures p50/p95/TTFT/WS/re-sim; tune routing/caching.
  - Deps: T6.1 · Accept: budgets met or documented — satisfies NFR-2.
- ✅ **T6.3 Anti-tamper hardening verification** — fuzz malformed/replayed/forged frames; token-theft test; client audit; telemetry hook; WSS/TLS documented.
  - Deps: Wave 5 · Accept: fuzz green; audit checklist evidenced — satisfies NFR-5.
- ✅ **T6.4 Docs, quickstart, final balance pass** — complete GDD; final balance; README quickstart <15min; runbook.
  - Deps: T6.1 · Accept: fresh clone runs stack <15min; `docs-check` green.

> [!TIP]
> **Wave 6 done-claim** — all eval gates pass; latency budgets met/documented; hardening verified; docs complete.

## 🔴 Final verification wave (parallel after Wave 6; all APPROVE)

> [!CAUTION]
> **Every item must APPROVE** — results surfaced before declaring complete.

- **F1 Plan compliance** — every task's acceptance met with evidence; `docs-check` green; no out-of-scope additions.
- **F2 Code quality** — `commit_encounter` sole mutator (grep); provenance forcing; client escapes server strings; sim conformance green; no LLM stat writes; no client content of value.
- **F3 Manual QA** — human plays the full loop (parry/riposte feel → market/shrine/boss → skill unlock → return → resume-after-restart).
- **F4 Scope fidelity** — OUT list respected (no generated assets/multiplayer/offline/dice/recording/PvP/3D).

---

## Execution rules

1. One todo = one atomic commit (conventional: `feat|fix|test|docs|chore|perf(scope)`).
2. Any commit touching `server/app`, `client/`, or `catalog/` must include its doc updates — `docs-check` fails otherwise.
3. Agent-executed QA (happy + failure) with evidence; self-report is never acceptance.
4. Determinism contracts enforced from Wave 2 (no module-level `random`/`randf()`, no wall-clock in sim, fixed entity order, seeded PRNG).

## Related documentation

- [spec.md](spec.md) — WHAT (the FR/NFR/invariants each task satisfies)
- [plan.md](plan.md) — HOW (the module design each task implements)
- [docs/05-protocol.md](../docs/05-protocol.md) — protocol (T1.2)
- [docs/STYLE.md](../docs/STYLE.md) — doc conventions (T1.6)

## 🩸 Wave 7 — Gap closure: durable fight lifecycle + live director (depends: Wave 6)

> [!CAUTION]
> Final-verification audit found these documented behaviors absent from code. Each task cites the FR it satisfies.

- ✅ **T7.1 Durable fights** — `fights` table (setup/log/fail_count/status); acked batches persisted (debounced); resume reloads open fights; crash/restart resumes the same fight.
  - Deps: Wave 5 · Accept: kill/restart between input and submit → same fight, same log — satisfies FR-2.4, US6.
- ✅ **T7.2 Death = permadeath** — verified loss (`php<=0`) sets `session.terminal`, persists, emits `game_over`; further actions rejected `session_terminal`.
  - Deps: T7.1 · Accept: scripted loss → `game_over` + terminal — satisfies FR-4.1.
- ✅ **T7.3 Flee resolution + reject cap** — tick limit (`FIGHT_TICK_LIMIT`) forces flee (no rewards); `verified:false` increments persisted fail_count; ≥2 → flee; rejects hit telemetry hook.
  - Deps: T7.1 · Accept: forged claims ×3 → flee on 3rd; 36k-tick fight flees — satisfies FR-1.5, FR-2.3.
- ✅ **T7.4 Boss gate** — `descend` off a boss floor requires that boss in `session.bosses_defeated`.
  - Deps: Wave 4 · Accept: descend before boss kill → `rule_violation` — satisfies FR-3.1.
- ✅ **T7.5 Live director via LangGraph** — `talk` routed through compiled graph (narrate node streams real prose); attack runs `encounter_gen`: compose_and_verify → `commit_encounter` writes the room → fight uses committed stats; `decision_request`/resume wired for parked interrupts.
  - Deps: T6-key LLM · Accept: two builds → different composed variants pre-clamp; tampered variant never reaches a room — satisfies FR-5.1/5.2, US5, D4.
- ✅ **T7.6 Behavior tables in sim** — weighted enemy actions from catalog `behavior_table`, drawn from the shared xorshift; byte-identical Python≡GDScript; fights feed committed enemy tables.
  - Deps: T7.5 · Accept: conformance green incl. table-driven cases — satisfies FR-1.4.
- ✅ **T7.7 Batched fight_input** — optional `batch[]` accepted alongside single-tick fields; one ack per frame; persistence debounced to batch boundaries.
  - Deps: T7.1 · Accept: 60-tick batch → one ack, rate limiter quiet — satisfies FR-2.1.
- ✅ **T7.8 Client parity** *(closed by T8.4 — dynamic fight_id, behavior_table mirror, parry/riposte inputs)* — dynamic `fight_id` from `fight_begin`; parry input + riposte follow-up in HUD; conformance re-run in-engine.
  - Deps: T7.5–T7.7 · Accept: scripted parry→riposte vs real server `verified:true`.

> [!TIP]
> **Wave 7 done-claim** — every FR acceptance re-runnable green; docs match code (no documented-but-absent behavior).

## 🖼️ Wave 8 — Client art & feel (depends: Wave 7; assets_pool/pixel-art curated)

> [!NOTE]
> ~~Render-style: side-view pivot.~~ **SUPERSEDED (user reference image): the target is 2.5-D top-down (≈30° view, Hyper-Light-Drifter-like)** — circle-strafe enemies, dash *through* them, punish the rear arc. Side-view arena code remains as fallback; Wave 8 render tasks now target the top-down arena. The sim gains a true second axis: euclidean ranges, enemy approach movement, facing-tracked **backstab arc** (dash-through → rear punish), all integer-deterministic in both cores.

- ✅ **T8.1 Art foundation** — vendor chosen CC0 tiles (Kenney roguelike/caves) into `client/assets/art/`; FloorRenderer renders real tilesets with per-sector theme variation.
  - Deps: Wave 5 · Accept: same-seed floor screenshot shows themed tiles, not placeholder diamonds.
- ✅ **T8.2 Hero sheet + combat anims** — vendor rvros *Animated Pixel Adventurer* (CC0) or aamatniekss *Hero Knight*; AnimatedSprite2D idle/run/attack/roll/parry/hurt/death driven by sim state/events.
  - Deps: assets_pool · Accept: scripted fight shows anim transitions matching server events.
- ✅ **T8.3 Enemy dressing** — Gothicvania skeleton/necromancer replaces enemy rectangles; necromancer summon set reserved for boss floors.
  - Deps: T8.1 · Accept: enemy rooms render themed foes.
- ✅ **T8.4 Client parity (closes T7.8)** — dynamic `fight_id` from `fight_begin` (incl. `behavior_table` into client sim); parry input + riposte follow-up window (`prip==1`).
  - Deps: T8.2 · Accept: scripted parry→riposte against the real server → `verified:true`.
- ⏳ **T8.5 HUD & menus skin** — Kenney UI RPG on HP/stamina/posture bars, market/shop panels, decision_request prompts. *(deferred — functional ColorRect bars ship now; Kenney skin is polish backlog)*
  - Deps: T8.1 · Accept: visual pass across all scenes.

- ⏳ **T8.6 2.5-D sim + arena (per user reference)** — sim: euclidean attack/strike ranges, enemy approach movement (`ENEMY_SPEED`, axis-split integer steps), enemy facing (`efx/efy`) set on strike/approach, backstab ×1.5 when attacking from the rear arc (`facing · attacker_rel < 0`); byte-identical both cores. Client: `py` maps to screen-y inside the floor band (y-sorted), Kenney roguelike tiles replace ColorRect ground, dash-through/backstab feel pass.
  - Deps: T8.2 · Accept: conformance regen green (2-D trajectories); circle-strafe + dash-through → backstab ×1.5 lands `verified:true`; screenshot matches reference framing.

> [!TIP]
> **Wave 8 done-claim** — the F3 manual-QA matrix is fully playable *and* readable as a soulslike: descend → parry/riposte fight (feel!) → shrine light → market → boss → skill unlock → return home → resume after restart.

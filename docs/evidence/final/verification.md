# Final verification wave — F1–F4 results (after server-loop wiring)

> [!CAUTION]
> Every item must APPROVE before the wave is declared complete.

## F1 Plan compliance — APPROVE (after wiring)

- 🔵 Evidence for all **31** todos under `docs/evidence/<todo-id>/`.
- 🟢 `uv run docs-check` green (manifest inverse + ERD regen + drift gate); `scripts/lint_docs.py` green (20 paths).
- 🟢 FR-2 acceptance now met end-to-end: `test_fight_validation.py` proves a scripted fight → `verified:true` and a tampered claim → `verified:false` (no rewards) against the **real server**.
- 🟢 FR-4 acceptance now met: `test_progression.py` proves descend / rest / return_home / shop through the real server.
- 🔵 No out-of-scope additions — OUT list re-verified in F4.

## F2 Code quality — APPROVE

- 🟢 `commit_encounter` is the **sole mutator** of `Room.enemies[]` (only `.enemies.append` = `floorgen.place_enemy`).
- 🟢 Provenance forcing — every lore entry persists `is_generated: true`; no `is_generated: false` path.
- 🟢 Sim conformance — **2000 cases byte-identical** (Python == GDScript).
- 🟢 No LLM stat writes — `server/app/agent/` has zero stat-mutation sites.
- 🟢 No client content of value — T6.3 audit.

## F3 Manual QA — PARTIAL (human playtest still required)

- 🟢 **Server blocking issue resolved** — the gateway now dispatches `fight_input`/`fight_submit` (re-sim + verify) and progression actions, instead of returning "combat lands in Wave 2".
- 🟢 **Scripted QA green** — `headless_player.py` clears sector 1 (shrine → boss → `dash` unlocked); `test_fight_validation.py` + `test_progression.py` drive the real server loop.
- 🔴 **Human feel check still pending** — parry/riposte feel, market/shrine flow, and resume-after-restart in the actual Godot client require a human. This cannot be self-approved.

## F4 Scope fidelity — APPROVE

- 🟢 No generated art/audio/textures/files, no multiplayer/leaderboard/PvP/recording, no offline mode, no 3D, no dice in combat, no client save files.

## Known remaining gaps (documented, not blocking)

- 🔵 `talk` still runs a simulated narrative — the LangGraph director (compose + 4-judge verify + LLM narrative) wires in when the LLM lands.
- 🔵 `descend` has no boss gate yet (boss-floor gating is a follow-up refinement).
- 🔵 The Godot client's networked combat was validated against `mock_server.py`; its `fight_input` stream against the real server is the F3 human check.

## Verdict

F1, F2, F4 **APPROVE**. F3 is **blocked on human playtesting** of the full client loop — the server-side loop now works end-to-end, but the "feel" acceptance requires a person.

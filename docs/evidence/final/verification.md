# Final verification wave — F1–F4 results

> [!CAUTION]
> Every item must APPROVE before the wave is declared complete.

## F1 Plan compliance — APPROVE

- 🔵 Evidence for all **31** todos under `docs/evidence/<todo-id>/` (6 gaps closed in this wave: t1.4, t2.2, t3.1–t3.4 — all test-proven).
- 🟢 `uv run docs-check` green (manifest inverse + ERD regen + drift gate).
- 🟢 `scripts/lint_docs.py` green (20 paths).
- 🟢 No out-of-scope additions — OUT list re-verified in F4.

## F2 Code quality — APPROVE

- 🟢 `commit_encounter` is the **sole mutator** of `Room.enemies[]` — the only `.enemies.append` in the codebase is `floorgen.place_enemy`, called exclusively from `commit_encounter`.
- 🟢 Provenance forcing — every lore entry persists `is_generated: true` (`LoreStore.add`, `save_lore_fact`, `rag/lore.py`); no `is_generated: false` path exists.
- 🟢 Sim conformance — **2000 cases byte-identical** (Python == GDScript).
- 🟢 No LLM stat writes — `server/app/agent/` has zero stat-mutation sites.
- 🟢 No client content of value — T6.3 audit (no save file, deterministic PRNG).

## F3 Manual QA — PARTIAL (human playtest required)

- 🟢 **Scripted QA green**: `headless_player.py` clears sector 1 (shrine → boss "The Violence" defeated → `dash` unlocked).
- 🔴 **Human feel check pending** — parry/riposte feel, market/shrine flow, and resume-after-restart require a human playing the Godot client. This cannot be self-approved.

## F4 Scope fidelity — APPROVE

- 🟢 No generated art/audio/textures/files (only catalog-data composition; the client's `_make_atlas_texture` is an in-memory placeholder tile, not asset generation).
- 🟢 No multiplayer / leaderboard / PvP / recording (only langsmith dependency internals in `.venv`).
- 🟢 No offline mode, no 3D (`Node3D`/`MeshInstance3D` absent), no dice in combat (conformance + sim-discipline green), no client save files.

## Verdict

F1, F2, F4 **APPROVE**. F3 is **blocked on human playtesting** of the full client loop — scripted/headless QA passes, but the "feel" acceptance requires a person.

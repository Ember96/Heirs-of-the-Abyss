# System design

> Status: **in progress** — sim core documented (T2.3); authority model + `commit_encounter` + engine-first routing land in Wave 3.

Module layout, authority model (engine owns stats), single-write invariant (commit_encounter), engine-first routing, concurrency model

## Sim core (shared, dual-language)

The combat sim is a pure function `(state, inputs, seed) → (state, events)` implemented identically in **Python** (`server/app/game/sim/core.py`) and **GDScript** (`client/scripts/sim_core.gd`), proven **byte-identical** by a 2000-case conformance corpus (`catalog/sim_corpus/corpus.json`).

> [!IMPORTANT]
> Combat is **dice-free**: damage is `max(1, atk − def)` × a deterministic mechanical multiplier (×1.5 stagger = `(d*3+1)>>1`); no RNG crits.

- **Integer/fixed-point** — positions in tile-units ×1000; no floats in sim paths.
- **Fixed 60 Hz tick** — tick counters, never wall-clock.
- **32-bit xorshift** PRNG — values stay in `0..2^32-1`, so the arithmetic is identical in both languages (no sign-extension ambiguity).
- **Per-fight RNG isolation** — a fresh `SeededRandom(fight_seed)` is created per re-sim and consumed only by the sim.
- **Canonical `state_hash`** — SHA-256 over the serialized end-state (fixed field order) + tick + sim_version.

## See also

- [System architecture (D1)](02-architecture.md)
- [Data model (ERD)](06-data-model.md)
- [Agent design — commit_encounter](07-agent-design.md)
- [Specification §6 — invariants](../specs/spec.md#6-invariants-must-hold-verified-by-tests)

<!-- content to follow -->
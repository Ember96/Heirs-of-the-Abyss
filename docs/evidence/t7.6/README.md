# T7.6 evidence — behavior tables drive enemy strikes

> [!TIP]
> FR-1.4 is live in BOTH cores: a second xorshift draw selects a weighted action from the catalog `behavior_table`; strike damage comes from the table (`max(1, damage - pdef)`), table-less enemies keep `eatk`. Conformance corpus regenerated with ~50% table-bearing cases: **2000 cases byte-identical (Python == GDScript)**.

> [!NOTE]
> Unit proofs (`tests/test_behavior.py`): single-entry table pins strike damage exactly (13→8 after def); empty table falls back to eatk (8→3); multi-entry strikes stay within table values {20,4}; same-seed trajectories are canonically identical. Committed enemies carry their catalog table end-to-end: director variant → `fight_begin.opponent_spec.behavior_table` → `FightSession.setup` → sim state.

# T8.4 evidence — client parity (closes T7.8)

> [!TIP]
> `fight_begin.opponent_spec.behavior_table` + additive `player_spec{attack,defense}` flow into the client mirror (`FightController.start_fight(...bt)`), so GDScript replays the identical trajectory the server re-sims; submissions use the REAL dynamic `fight_id`. Inputs: A/D move · S/L guard · X/J attack (auto-riposte when `prip==1`) · C/K roll · P parry. Server-side parry/riposte determinism: `tests/test_parry.py`.

# T7.7 evidence — batched fight_input + NFR-6 wiring

> [!TIP]
> `tests/test_batch_input.py`: a 60-tick batch yields exactly ONE ack (`last_tick==60`); overlapping batches dedupe idempotently (10 then 5..15 → 15); malformed items reject the frame (`frame_invalid`) without touching the log. Retention (30d age / 100MB budget, oldest-first cascade incl. fights) enforced at every server start via app lifespan — `test_prune_oversized_evicts_oldest_first`.

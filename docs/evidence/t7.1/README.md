# T7.1 evidence — durable fights

> [!TIP]
> Crash/restart mid-fight resumes the identical fight: `test_crash_restart_resumes_same_fight` persists the row on create + debounced input flush, reloads open fights on `resume`, then finishes with `verified:true` and intact rewards (`gold == 20`). Row status transitions land in SQLite (`fights` table, cascade-pruned with the session).

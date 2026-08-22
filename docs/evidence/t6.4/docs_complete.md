# T6.4 evidence — docs, quickstart, final balance pass

> [!TIP]
> GDD + runbook + evals + corpus finalized; balance gates green; `docs-check` + style lint green.

## Docs completed

- `docs/01-gdd.md` — enemies + balance sections added; status → complete.
- `docs/10-runbook.md` — quickstart, env vars, provider switching, session ops, latency/cost.
- `docs/11-evals.md` — thresholds (NFR-8), how to run, latency budgets.
- `docs/09-ai-rag-corpus.md` — 14 sources + licenses.
- `docs/02/04/06/07/08` — stale "skeleton" status lines → complete.

## Final balance (vs T6.1 gates)

```
schema_valid:   1.00  (>= 0.95)  PASS
balance:        1.00  (>= 1.0)   PASS
catalog_ids:    1.00  (>= 1.0)   PASS
```

## Gates

- `docs-check` — OK (manifest inverse + ERD regen).
- `scripts/lint_docs.py` — 20 paths, pass.
- `uv run pytest` — 197 passed.
- README quickstart — fresh clone → stack in <15 min (documented in runbook).

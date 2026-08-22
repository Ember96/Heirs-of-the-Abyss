# Evals

> Status: **complete** — deterministic code evaluators + thresholds + runner (T6.1).

## Thresholds (NFR-8)

> [!NOTE]
> `uv run evals` checks three deterministic gates; LangSmith tracing + LLM-as-judge (narrative quality ≥ 80%, rule adherence ≥ 95%) wire when `LANGSMITH_API_KEY` is set.

| Gate | Threshold |
|------|-----------|
| `schema_valid` | ≥ 0.95 |
| `balance` | ≥ 1.0 |
| `catalog_ids` | ≥ 1.0 |

## How to run

> [!TIP]
> `cd server && uv run evals` — composes 100 variants (5 tiers × 20) and reports each gate against its threshold. Exit 0 = all pass.

## Latency budgets (T6.2)

> [!NOTE]
> See `server/app/evals/latency.py`. Worst-case fight re-simulation: **16 ms** (budget 1000 ms). LLM metrics deferred until wired.

## See also

- [Specification — NFR-8 thresholds](../specs/spec.md#5-non-functional-requirements)
- [Runbook — how to run](10-runbook.md)
- [Latency evidence](../evidence/t6.2/latency.json)

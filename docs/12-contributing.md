# Contributing

> The canonical contributor guide is [`CONTRIBUTING.md`](../../CONTRIBUTING.md) at the repo root. This page documents the project-specific extension recipes and the doc-update rules.

## Documentation style — mandatory

All Markdown and Mermaid **must** follow [`STYLE.md`](STYLE.md). The four statement natures are color-encoded and fixed:

> **Legend** — 🟠 critical rule/invariant (`> [!WARNING]`) · 🟢 success/done (`> [!TIP]`) · 🔴 problem/must-not (`> [!CAUTION]`) · 🔵 info (`> [!NOTE]`)

> [!WARNING]
> Run `python3 scripts/lint_docs.py` before committing any docs change. A change that fails the lint is not done.

## How to extend the project

| You want to… | Where |
|--------------|-------|
| Add a **class** | `catalog/` (stats + starting gear + build-tag bias) |
| Add an **enemy type** | `catalog/` (stat profile + behavior table) |
| Add a **boss** | `catalog/` (arena behavior + skill unlock) |
| Add a **room type** | `server/app/game/floorgen.py` (layer-state rules) + `docs/04-game-states.md` |
| Add a **boss skill** | `catalog/` (per-level effect formulas) |
| Add a **catalog entry** | `catalog/` (with `entity_kind`, `tags[]`, `tier`, `stat_profile`, `is_canonical`) |

Every change to `server/app`, `client/`, or `catalog/` **must** carry its doc update in the same commit — `docs-check` fails otherwise.

## Commit rules

Conventional commits: `feat|fix|test|docs|chore|perf(scope): message`; scope ∈ `server|agent|rag|sim|corpus|client|catalog|evals|security|docs`.

## License

MIT — see [`LICENSE`](../../LICENSE). The bundled corpus (`catalog/corpus/`) carries per-source licenses; see `catalog/corpus/manifest.json`.

## See also

- [Style guide — mandatory conventions](STYLE.md)
- [Root contributor guide](../CONTRIBUTING.md)

# Contributing to EndlessDungeon

Thanks for contributing. This project is meant to be **shared and well-documented** — so a contribution that changes code or docs must keep the documentation coherent.

## Documentation style — mandatory

All Markdown and Mermaid diagrams **must** follow [`docs/STYLE.md`](docs/STYLE.md). The four statement natures are color-encoded and fixed:

| Nature | Color | Alert | Mermaid class |
|--------|-------|-------|---------------|
| Critical rule / invariant | 🟠 orange | `> [!WARNING]` / `> [!IMPORTANT]` | `crit` |
| Success / goal / done | 🟢 green | `> [!TIP]` | `ok` |
| Problem / must-not / risk | 🔴 red | `> [!CAUTION]` | `bad` |
| Info / context | 🔵 blue | `> [!NOTE]` | `info` |

**Before opening a PR, run:**

```bash
python3 scripts/lint_docs.py          # fails on any style violation
cd server && uv run pytest            # must stay green
```

Do not introduce a new color or alert type for these four natures, and cross-reference related docs (a `## See also` section) in every `docs/` + `specs/` file. A PR that fails the lint will not be merged until fixed.

## Development workflow

1. **Fork & branch** from `main`; one focused change per PR.
2. **Commit** conventionally: `feat|fix|test|docs|chore|perf(scope): message`.
3. **Update docs** in the same commit as the code change — any change touching `server/app`, `client/`, or `catalog/` must carry its doc updates (enforced by `docs:check` from T1.6).
4. **Add tests** for new behavior; evidence under `docs/evidence/<todo-id>/`.
5. **Open a PR** — CI/verification must pass before review.

## Getting started

```bash
cd server && uv sync          # install pinned deps
uv run pytest                 # run tests
cd ../client && godot --path . --editor   # open the client in Godot 4.7.2
```

See [`README.md`](README.md) for the full quickstart and [`specs/`](specs/) for the spec-driven plan.

## License

MIT — see [LICENSE](LICENSE). The bundled game-design corpus (`catalog/corpus/`) carries its own per-source licenses; see `catalog/corpus/manifest.json`.

# Documentation Style Guide

> **Canonical reference** — every Markdown document and Mermaid diagram in this repository **MUST** follow this guide. Enforced by `scripts/lint_docs.py` and (from T1.6) the `docs-check` drift gate. Agents: see `AGENTS.md`. Humans: see `CONTRIBUTING.md`.

## 1. The four statement colors

Every significant statement carries one of four natures, encoded with a **consistent color + shape**. This is the core convention — a reader must be able to scan for color and know what kind of claim they're looking at.

| Nature | Emoji | Meaning | Markdown alert | Mermaid `classDef` |
|--------|-------|---------|----------------|--------------------|
| 🟠 **Critical** | 🟠 / ⚠️ | hard rule, invariant, single-write-path, gate | `> [!WARNING]` (or `> [!IMPORTANT]` for the single most-important invariant) | `crit` |
| 🟢 **Success** | 🟢 / ✅ | good result, goal, done-claim, checkpoint, pass | `> [!TIP]` | `ok` |
| 🔴 **Problem** | 🔴 / ❌ | risk, must-not, non-goal, failure, fallback, terminal | `> [!CAUTION]` | `bad` |
| 🔵 **Info** | 🔵 / ℹ️ | context, neutral fact, definition | `> [!NOTE]` | `info` |

Rules:

- **Never** invent a new color for one of these four natures. If a statement is a critical rule, it is orange — always.
- A statement that isn't one of these four natures stays **uncolored** (plain text).
- Inline emphasis of a single colored term may use the emoji (🟠🟢🔴🔵) or bold, but the surrounding callout/alert must carry the structural color.

## 2. Markdown alerts (callout boxes)

Use GitHub-style alerts for block-level statements. Only these five exist — no others:

| Alert | Use for |
|-------|---------|
| `> [!NOTE]` | 🔵 info / context |
| `> [!TIP]` | 🟢 success / goal / done-claim / checkpoint |
| `> [!IMPORTANT]` | 🟠 the single most-important invariant (authority model, single-write-path) |
| `> [!WARNING]` | 🟠 critical rules / constraints (no-RNG, invariants) |
| `> [!CAUTION]` | 🔴 problems / must-not / non-goals / risks |

```markdown
> [!WARNING]
> **No hit-chance rolls, no damage variance, no RNG crits.** Crits are mechanical, never random.
```

## 3. Mermaid diagrams

### 3.1 The canonical palette (copy-paste these four `classDef`s)

```mermaid
classDef crit fill:#FFF3E0,stroke:#F57C00,stroke-width:2px,color:#E65100,font-weight:bold
classDef ok   fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px,color:#1B5E20,font-weight:bold
classDef bad  fill:#FFEBEE,stroke:#C62828,stroke-width:2px,color:#B71C1C
classDef info fill:#E3F2FD,stroke:#1565C0,stroke-width:2px,color:#0D47A1
```

### 3.2 Applying color

- **flowchart** / **graph**: append `:::className` to the node — `H["bonfire → checkpoint"]:::ok`.
- **stateDiagram-v2**: add `class STATE_NAME className` after the states — `class GAMEOVER bad`.
- Highlight **key** nodes only (the single-write path, the terminal state, the checkpoint, the gate). Do not color everything — an all-colored diagram has no contrast.
- **sequenceDiagram** and **erDiagram** do **not** support `classDef`. For those, convey the same meaning in prose (e.g. a `> [!NOTE]` above the diagram) rather than forcing broken syntax.

### 3.3 Legend line

Every file containing a Mermaid diagram **MUST** include a legend line directly above the `## Diagrams` section:

```markdown
> **Diagram legend** — 🟠 critical/gate · 🟢 checkpoint/success · 🔴 terminal/failure · 🔵 info
```

## 4. Roadmap & headings

- Roadmap **phases** use these emoji, fixed forever:
  `🏗️` Foundation · `⚙️` Core · `🧠` Director · `📚` RAG · `🗡️` Client · `🛡️` Hardening · `🔴` Final verification.
- Heading hierarchy is the size convention: `#` doc title → `##` section/wave → `###` sub-section/task group. Don't skip levels.
- Task/status markers: `✅` done · `⏳` pending · `🔴` blocking/final-gate.

## 5. Snippets & emphasis

- Inline code for identifiers, paths, fields, and frame names: `` `commit_encounter` ``, `` `state_sync` ``.
- Bold for the **load-bearing word** in a sentence, not whole sentences.
- Tables over prose when comparing parallel items (risks↔mitigations, goals, thresholds).

## 6. Cross-references (mandatory)

Every documentation file under `docs/` and `specs/` **must** link to at least one other doc that describes a concept it uses. If a file mentions `commit_encounter`, the protocol, the sim core, or the verifiers, it links to the file that owns that concept.

- Add a `## See also` section listing related docs (see any of `docs/01-gdd.md` … `docs/13-security.md`).
- Link the concept where it appears, e.g. `[WS v1 protocol](05-protocol.md)`.
- Cross-file links are relative: `02-architecture.md` within `docs/`, `../specs/spec.md#4-functional-requirements` from `docs/` to `specs/`.

The canonical concept → file map:

| Concept | Canonical location |
|---------|--------------------|
| Authority model / engine-first routing / single-write path | `docs/03-system-design.md` |
| `commit_encounter` | `docs/07-agent-design.md` (D4/D9), `docs/03-system-design.md` |
| Deterministic combat / sim core | `docs/04-game-states.md` (D7) |
| WS protocol / envelope / HMAC / resume | `docs/05-protocol.md` |
| Verifier agents (4 judges) | `docs/07-agent-design.md` (D9) |
| RAG / catalog / corpus | `docs/08-content-catalog.md`, `docs/09-ai-rag-corpus.md` |
| Floor template / pacing | `docs/08-content-catalog.md` (D10) |
| Data model / Pydantic | `docs/06-data-model.md` |
| Anti-tamper / threat model | `docs/13-security.md` |
| Evals / thresholds | `docs/11-evals.md` |
| Env vars / ops | `docs/10-runbook.md` |

## 7. Compliance

```bash
python3 scripts/lint_docs.py          # fail on any violation
```

The lint checks: alert-type whitelist, Mermaid `classDef` palette conformance, legend presence in diagram-bearing files, and **cross-reference presence** (a `docs/`/`specs/` file with no links to other docs fails). A docs change that violates the guide is treated the same as a code change that breaks a test — **it does not merge**.

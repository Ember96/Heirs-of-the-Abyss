#!/usr/bin/env python3
"""Documentation style lint — enforces docs/STYLE.md.

Checks (fail on any violation):
  1. Alert types are from the standard set  {NOTE, TIP, IMPORTANT, WARNING, CAUTION}.
  2. Mermaid classDef names + fill/stroke match the canonical 4-color palette.
  3. Every file containing a Mermaid diagram carries a legend line.
  4. Every docs/ + specs/ file links to at least one other doc (cross-reference).

Usage:
  python3 scripts/lint_docs.py [path ...]     # default: docs/, specs/, *.md

Exit 0 on pass, 1 on violations.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ── canonical conventions (single source of truth — keep in sync with docs/STYLE.md) ──
STANDARD_ALERTS = {"NOTE", "TIP", "IMPORTANT", "WARNING", "CAUTION"}

CANONICAL_CLASSDEF = {
    "crit": {"fill": "FFF3E0", "stroke": "F57C00"},
    "ok":   {"fill": "E8F5E9", "stroke": "2E7D32"},
    "bad":  {"fill": "FFEBEE", "stroke": "C62828"},
    "info": {"fill": "E3F2FD", "stroke": "1565C0"},
}

# the style guide documents the convention and contains canonical examples
SKIP = {"docs/STYLE.md"}

ALERT_RE = re.compile(r">\s*\[\!([A-Za-z]+)\]")
CLASSDEF_RE = re.compile(r"classDef\s+(\w+)\s+fill:#([0-9A-Fa-f]+),stroke:#([0-9A-Fa-f]+)")
MERMAID_RE = re.compile(r"```mermaid")
LEGEND_RE = re.compile(r"legend", re.IGNORECASE)
MDLINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
CROSSREF_RE = re.compile(r".*\.md(#[^)]*)?$")


def default_paths() -> list[Path]:
    root = Path(__file__).resolve().parent.parent
    paths = list((root / "docs").glob("*.md")) + list((root / "specs").glob("*.md"))
    paths += list(root.glob("*.md"))
    return sorted(paths)


def lint_file(path: Path) -> list[str]:
    root = Path(__file__).resolve().parent.parent
    try:
        rel = str(path.resolve().relative_to(root))
    except ValueError:
        rel = path.name  # outside repo — still lint, but cross-ref check is docs/specs-scoped
    if rel in SKIP:
        return []
    text = path.read_text(encoding="utf-8")
    violations: list[str] = []

    for m in ALERT_RE.finditer(text):
        if m.group(1).upper() not in STANDARD_ALERTS:
            violations.append(f"{rel}: non-standard alert type [{m.group(1)}] (allowed: {sorted(STANDARD_ALERTS)})")

    for m in CLASSDEF_RE.finditer(text):
        name, fill, stroke = m.group(1), m.group(2).upper(), m.group(3).upper()
        if name not in CANONICAL_CLASSDEF:
            violations.append(f"{rel}: non-standard classDef '{name}' (allowed: {sorted(CANONICAL_CLASSDEF)})")
            continue
        want = CANONICAL_CLASSDEF[name]
        if fill != want["fill"] or stroke != want["stroke"]:
            violations.append(
                f"{rel}: classDef '{name}' off-palette — got fill:#{fill}/stroke:#{stroke}, "
                f"want fill:#{want['fill']}/stroke:#{want['stroke']}"
            )

    if MERMAID_RE.search(text) and not LEGEND_RE.search(text):
        violations.append(f"{rel}: contains a Mermaid diagram but no legend line")

    if rel.startswith(("docs/", "specs/")) and rel not in SKIP:
        crossref = any(CROSSREF_RE.match(m.group(1).strip()) for m in MDLINK_RE.finditer(text))
        if not crossref:
            violations.append(f"{rel}: no cross-reference links — add a 'See also' section linking related docs")

    return violations


def main(argv: list[str]) -> int:
    if argv:
        paths = [Path(p) for p in argv if Path(p).exists()]
    else:
        paths = default_paths()

    all_violations: list[str] = []
    for p in paths:
        if p.is_dir():
            for f in sorted(p.glob("*.md")):
                all_violations += lint_file(f)
        elif p.suffix == ".md":
            all_violations += lint_file(p)

    if not all_violations:
        print(f"✓ docs style lint passed ({len(paths)} paths)")
        return 0

    print(f"✗ {len(all_violations)} violation(s):\n")
    for v in all_violations:
        print(f"  - {v}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""`docs:check` — the living-docs drift gate (T1.6).

Enforces, in order:
  1. style lint (alert whitelist, Mermaid palette, legend, cross-references)
  2. code→doc manifest structure (each mapping targets ≥1 existing doc)
  3. manifest inverse check (every source file is listed or derivable-covered)
  4. derivable-doc regeneration + diff (stub until models land in T2.1)

Exits 0 on a clean tree, 1 on any violation.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST_PATH = ROOT / "docs" / "manifest.json"
DOC_DIR = ROOT / "docs"
LINT_SCRIPT = ROOT / "scripts" / "lint_docs.py"

SOURCE_EXTENSIONS = (
    ("server/app", "*.py"),
    ("client", "*.gd"),
    ("catalog", "*.json"),
)
SKIP_DIR_PARTS = {".godot", "__pycache__", ".venv"}


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def collect_source_files() -> set[str]:
    files: set[str] = set()
    for directory, pattern in SOURCE_EXTENSIONS:
        base = ROOT / directory
        if not base.exists():
            continue
        for path in base.rglob(pattern):
            if any(part in SKIP_DIR_PARTS for part in path.parts):
                continue
            if path.name.startswith("test_") or path.name == "__init__.py":
                continue
            files.add(str(path.relative_to(ROOT)))
    return files


def manifest_structure_check(manifest: dict) -> list[str]:
    violations: list[str] = []
    doc_names = {p.name for p in DOC_DIR.glob("*.md")}
    for code_path, doc_list in manifest.get("mappings", {}).items():
        if not doc_list:
            violations.append(f"{code_path}: empty doc mapping (must target >=1 existing doc)")
            continue
        for doc in doc_list:
            if Path(doc).name not in doc_names:
                violations.append(f"{code_path}: doc '{doc}' does not exist")
    return violations


def manifest_inverse_check(manifest: dict) -> list[str]:
    covered = set(manifest.get("mappings", {}).keys()) | set(manifest.get("derivable", {}).keys())
    return [f"unlisted source file: {f}" for f in sorted(collect_source_files() - covered)]


def run_style_lint() -> list[str]:
    result = subprocess.run(
        [sys.executable, str(LINT_SCRIPT)], capture_output=True, text=True, cwd=str(ROOT)
    )
    return [] if result.returncode == 0 else [result.stdout.strip()]


def generate_erd() -> str:
    import inspect

    from pydantic import BaseModel

    from app.game import models as m

    lines = ["erDiagram"]
    for name in sorted(dir(m)):
        obj = getattr(m, name)
        if not (inspect.isclass(obj) and issubclass(obj, BaseModel) and obj.__module__ == m.__name__):
            continue
        if name in ("GameModel", "RoomType"):
            continue
        lines.append(f"  {name} {{")
        for field in obj.model_fields:
            lines.append(f"    string {field}")
        lines.append("  }")
    return "\n".join(lines)


def regenerate_derivable_docs(manifest: dict) -> list[str]:
    violations: list[str] = []
    if (ROOT / "server/app/game/models.py").exists():
        generated = generate_erd()
        doc = (DOC_DIR / "06-data-model.md").read_text(encoding="utf-8")
        start = doc.find("<!-- ERD-GENERATED-START -->")
        end = doc.find("<!-- ERD-GENERATED-END -->")
        if start == -1 or end == -1:
            violations.append("docs/06-data-model.md: missing ERD generation markers")
        else:
            expected = (
                "<!-- ERD-GENERATED-START -->\n\n```mermaid\n"
                f"{generated}\n```\n\n<!-- ERD-GENERATED-END -->"
            )
            current = doc[start:end + len("<!-- ERD-GENERATED-END -->")]
            if current != expected:
                violations.append("docs/06-data-model.md: ERD drifted from models.py — regenerate it")
    return violations


def main() -> int:
    violations: list[str] = []
    violations += run_style_lint()

    manifest = load_manifest()
    violations += manifest_structure_check(manifest)
    violations += manifest_inverse_check(manifest)
    violations += regenerate_derivable_docs(manifest)

    if violations:
        print("docs:check FAILED")
        for v in violations:
            print(f"  - {v}")
        return 1
    print("docs:check OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

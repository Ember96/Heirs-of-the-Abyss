"""Lore quarantine (T4.5) — per-session ring buffer, provenance, wrap-as-data.

Generated lore is a per-session ring buffer (oldest pruned past the cap), and
retrieval is always filtered by session_id so it can never leak across
sessions. On retrieval, lore is wrapped as untrusted data. Provenance is forced:
every entry persists as `is_generated`.
"""

from __future__ import annotations

MAX_LORE_ENTRIES = 500


class LoreRingBuffer:
    def __init__(self, max_entries: int = MAX_LORE_ENTRIES) -> None:
        self.max_entries = max_entries
        self._entries: list[dict] = []

    def add(self, session_id: str, fragment: str) -> dict:
        entry = {"session_id": session_id, "fragment": fragment, "is_generated": True}
        self._entries.append(entry)
        if len(self._entries) > self.max_entries:
            self._entries.pop(0)
        return entry

    def retrieve(self, session_id: str) -> list[dict]:
        return [e for e in self._entries if e["session_id"] == session_id]

    def size(self, session_id: str | None = None) -> int:
        if session_id is None:
            return len(self._entries)
        return sum(1 for e in self._entries if e["session_id"] == session_id)


def wrap_as_data(fragment: str) -> str:
    return f'<lore untrusted="true">\n{fragment}\n</lore>'


def moderate(text: str, enabled: bool = False) -> bool:
    if not enabled:
        return False
    return False

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class MemoryEntry:
    role: str
    content: str
    created_at: str

    @classmethod
    def now(cls, role: str, content: str) -> "MemoryEntry":
        return cls(role=role, content=content, created_at=datetime.now(timezone.utc).isoformat())


class LocalMemory:
    """Small append-only JSONL memory store.

    This is intentionally simple for the first release. It keeps history local,
    inspectable, and easy to replace later with Chroma, LanceDB, or SQLite.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, role: str, content: str) -> MemoryEntry:
        entry = MemoryEntry.now(role=role, content=content)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
        return entry

    def read_recent(self, limit: int = 20) -> list[MemoryEntry]:
        if not self.path.exists():
            return []
        rows = self._iter_entries()
        return list(rows)[-limit:]

    def search(self, query: str, limit: int = 10) -> list[MemoryEntry]:
        query_norm = query.casefold().strip()
        if not query_norm:
            return self.read_recent(limit)
        matches = [entry for entry in self._iter_entries() if query_norm in entry.content.casefold()]
        return matches[-limit:]

    def _iter_entries(self) -> Iterable[MemoryEntry]:
        if not self.path.exists():
            return []
        entries: list[MemoryEntry] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                    entries.append(MemoryEntry(**raw))
                except (json.JSONDecodeError, TypeError):
                    continue
        return entries

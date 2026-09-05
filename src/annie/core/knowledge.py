from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from annie.utils.private_files import ensure_private_directory, ensure_private_file


def _uid() -> str:
    return uuid.uuid4().hex[:8]


@dataclass
class KnowledgeStore:
    profile: str = ""
    facts: list[dict[str, Any]] = field(default_factory=list)
    goals: list[dict[str, Any]] = field(default_factory=list)
    journal: list[dict[str, Any]] = field(default_factory=list)


class LocalKnowledge:
    """Structured long-term memory: profile, facts, goals, journal."""

    def __init__(self, path: Path) -> None:
        self.path = path
        ensure_private_directory(self.path.parent)
        ensure_private_file(self.path)
        self._data = self._load()
        self._committed = deepcopy(self._data)

    def _load(self) -> KnowledgeStore:
        if not self.path.exists():
            return KnowledgeStore()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return KnowledgeStore(
                profile=str(raw.get("profile", "")),
                facts=list(raw.get("facts", [])),
                goals=list(raw.get("goals", [])),
                journal=list(raw.get("journal", [])),
            )
        except (json.JSONDecodeError, TypeError):
            return KnowledgeStore()

    def _save(self) -> None:
        temporary: Path | None = None
        try:
            # Replace only after a complete private file reaches disk. A failed
            # write must not leave a truncated file or a phantom in-memory save.
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent, prefix=".knowledge-", delete=False
            ) as handle:
                temporary = Path(handle.name)
                json.dump(asdict(self._data), handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        except Exception:
            self._data = deepcopy(self._committed)
            raise
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self._committed = deepcopy(self._data)

    def snapshot(self) -> dict[str, Any]:
        return asdict(self._data)

    def clear(self) -> None:
        self._data = KnowledgeStore()
        self._save()

    def remember(self, fact: str) -> dict[str, Any]:
        entry = {"id": _uid(), "text": fact.strip(), "t": time.time()}
        self._data.facts.append(entry)
        self._save()
        return {"saved": True, "id": entry["id"]}

    def recall(self, query: str) -> dict[str, Any]:
        needle = query.casefold().strip()
        hits: list[str] = []
        for item in [*self._data.facts, *self._data.journal]:
            text = str(item.get("text") or item.get("entry") or "")
            if not needle or needle in text.casefold():
                hits.append(text)
        return {"matches": hits[:8], "profile": self._data.profile or None}

    def update_profile(self, note: str) -> dict[str, Any]:
        line = note.strip()
        if self._data.profile:
            self._data.profile = f"{self._data.profile}\n{line}"
        else:
            self._data.profile = line
        self._save()
        return {"updated": True}

    def add_goal(self, goal: str) -> dict[str, Any]:
        entry = {"id": _uid(), "text": goal.strip(), "done": False, "t": time.time()}
        self._data.goals.append(entry)
        self._save()
        return {"added": True, "id": entry["id"]}

    def complete_goal(self, match: str) -> dict[str, Any]:
        needle = match.casefold()
        for goal in self._data.goals:
            if not goal.get("done") and needle in str(goal.get("text", "")).casefold():
                goal["done"] = True
                self._save()
                return {"completed": goal["text"]}
        return {"completed": None, "note": "no open goal matched"}

    def list_goals(self) -> dict[str, Any]:
        open_goals = [g["text"] for g in self._data.goals if not g.get("done")]
        return {"open": open_goals}

    def set_goal_state(self, item_id: str, done: bool) -> dict[str, Any]:
        """Update exactly one goal; repeated requests are idempotent."""
        for goal in self._data.goals:
            if goal.get("id") == item_id:
                goal["done"] = done
                self._save()
                return dict(goal)
        raise KeyError(item_id)

    def journal(self, entry: str) -> dict[str, Any]:
        row = {"id": _uid(), "entry": entry.strip(), "t": time.time()}
        self._data.journal.append(row)
        self._save()
        return {"saved": True, "id": row["id"]}

    def delete_item(self, kind: str, item_id: str | None = None) -> None:
        if kind == "profile":
            self._data.profile = ""
        elif kind == "goal" and item_id:
            self._data.goals = [g for g in self._data.goals if g.get("id") != item_id]
        elif kind == "fact" and item_id:
            self._data.facts = [f for f in self._data.facts if f.get("id") != item_id]
        elif kind == "journal" and item_id:
            self._data.journal = [j for j in self._data.journal if j.get("id") != item_id]
        else:
            raise ValueError("invalid delete request")
        self._save()

    def digest(self) -> str:
        open_goals = [f"- {g['text']}" for g in self._data.goals if not g.get("done")]
        facts = [f"- {f['text']}" for f in self._data.facts[-12:]]
        journal = [f"- {j['entry']}" for j in self._data.journal[-3:]]
        if not (self._data.profile or open_goals or facts or journal):
            return ""
        parts = ["\n\n[WHAT YOU ALREADY KNOW — from earlier sessions, on this device]"]
        if self._data.profile:
            parts.append(f"Profile:\n{self._data.profile}")
        if open_goals:
            parts.append("Open goals:\n" + "\n".join(open_goals))
        if facts:
            parts.append("Remembered:\n" + "\n".join(facts))
        if journal:
            parts.append("Recent journal:\n" + "\n".join(journal))
        parts.append("[Use this naturally. Update it with tools as you learn more.]")
        return "\n".join(parts)

from __future__ import annotations

import uuid
from typing import Any

from annie.core.knowledge import LocalKnowledge
from annie.core.memory import LocalMemory
from annie.core.settings import RuntimeSettings
from annie.repositories.base import (
    KnowledgeRepository,
    MemoryRepository,
    SettingsRepository,
)


class FileKnowledgeRepository(KnowledgeRepository):
    def __init__(self, store: LocalKnowledge) -> None:
        self.store = store

    async def snapshot(self, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        return self.store.snapshot()

    async def clear(self, user_id: uuid.UUID | None = None) -> None:
        self.store.clear()

    async def remember(self, fact: str, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        return self.store.remember(fact)

    async def recall(self, query: str, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        return self.store.recall(query)

    async def update_profile(self, note: str, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        return self.store.update_profile(note)

    async def add_goal(self, goal: str, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        return self.store.add_goal(goal)

    async def complete_goal(self, match: str, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        return self.store.complete_goal(match)

    async def list_goals(self, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        return self.store.list_goals()

    async def set_goal_state(self, item_id: str, done: bool, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        return self.store.set_goal_state(item_id, done)

    async def journal(self, entry: str, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        return self.store.journal(entry)

    async def delete_item(self, kind: str, item_id: str | None, user_id: uuid.UUID | None = None) -> None:
        self.store.delete_item(kind, item_id)

    async def digest(self, user_id: uuid.UUID | None = None) -> str:
        return self.store.digest()


class FileMemoryRepository(MemoryRepository):
    def __init__(self, store: LocalMemory) -> None:
        self.store = store

    async def append(self, role: str, content: str, user_id: uuid.UUID | None = None) -> None:
        self.store.append(role, content)

    async def read_recent(self, limit: int = 20, user_id: uuid.UUID | None = None) -> list[dict[str, str]]:
        return [
            {"role": e.role, "content": e.content, "created_at": e.created_at} for e in self.store.read_recent(limit)
        ]

    async def clear(self, user_id: uuid.UUID | None = None) -> None:
        self.store.clear()

    async def search(self, query: str, limit: int = 10, user_id: uuid.UUID | None = None) -> list[dict[str, str]]:
        return [
            {"role": e.role, "content": e.content, "created_at": e.created_at} for e in self.store.search(query, limit)
        ]


class FileSettingsRepository(SettingsRepository):
    def __init__(self, settings: RuntimeSettings, path) -> None:
        self.settings = settings
        self.path = path

    async def load(self, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        return self.settings.to_public_dict()

    async def save(self, payload: dict[str, Any], user_id: uuid.UUID | None = None) -> dict[str, Any]:
        self.settings.model = str(payload.get("model", self.settings.model))
        self.settings.ollama_url = str(payload.get("ollama_url", self.settings.ollama_url))
        self.settings.voice_url = str(payload.get("voice_url", self.settings.voice_url))
        self.settings.temperature = float(payload.get("temperature", self.settings.temperature))
        self.settings.tools_enabled = bool(payload.get("tools_enabled", self.settings.tools_enabled))
        self.settings.system_prompt = str(payload.get("system_prompt", self.settings.system_prompt))
        self.settings.save(self.path)
        return self.settings.to_public_dict()

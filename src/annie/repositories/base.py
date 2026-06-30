from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class UserRecord:
    id: uuid.UUID
    email: str
    password_hash: str
    is_active: bool


class UserRepository(ABC):
    @abstractmethod
    async def get_by_email(self, email: str) -> UserRecord | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, user_id: uuid.UUID) -> UserRecord | None:
        raise NotImplementedError

    @abstractmethod
    async def create(self, email: str, password_hash: str) -> UserRecord:
        raise NotImplementedError


class KnowledgeRepository(ABC):
    @abstractmethod
    async def snapshot(self, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def clear(self, user_id: uuid.UUID | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    async def remember(self, fact: str, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def recall(self, query: str, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def update_profile(self, note: str, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def add_goal(self, goal: str, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def complete_goal(self, match: str, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def list_goals(self, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def journal(self, entry: str, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def delete_item(self, kind: str, item_id: str | None, user_id: uuid.UUID | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    async def digest(self, user_id: uuid.UUID | None = None) -> str:
        raise NotImplementedError


class MemoryRepository(ABC):
    @abstractmethod
    async def append(self, role: str, content: str, user_id: uuid.UUID | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    async def read_recent(self, limit: int = 20, user_id: uuid.UUID | None = None) -> list[dict[str, str]]:
        raise NotImplementedError

    @abstractmethod
    async def clear(self, user_id: uuid.UUID | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    async def search(self, query: str, limit: int = 10, user_id: uuid.UUID | None = None) -> list[dict[str, str]]:
        raise NotImplementedError


class SettingsRepository(ABC):
    @abstractmethod
    async def load(self, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def save(self, payload: dict[str, Any], user_id: uuid.UUID | None = None) -> dict[str, Any]:
        raise NotImplementedError

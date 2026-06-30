from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from annie.core.config import AnnieConfig
from annie.core.knowledge import LocalKnowledge
from annie.core.memory import LocalMemory
from annie.core.session import SessionManager
from annie.core.settings import RuntimeSettings
from annie.env import is_production
from annie.api.deps.auth import get_current_user_id
from annie.repositories.file_adapters import FileKnowledgeRepository, FileMemoryRepository, FileSettingsRepository
from annie.services.cache_service import CacheService
from annie.services.chat_service import ChatService


@dataclass
class AppState:
    config: AnnieConfig
    cache: CacheService
    memory: LocalMemory
    knowledge: LocalKnowledge
    sessions: SessionManager
    settings: RuntimeSettings


def get_state(request: Request) -> AppState:
    return request.app.state.annie


async def _chat_service_impl(
    request: Request,
    user_id: uuid.UUID | None,
) -> AsyncIterator[ChatService]:
    state = request.app.state.annie
    if is_production():
        from annie.repositories.knowledge_repository import PostgresKnowledgeRepository
        from annie.repositories.memory_repository import PostgresMemoryRepository
        from annie.repositories.settings_repository import PostgresSettingsRepository

        factory = request.app.state.db_session_factory
        session = factory()
        try:
            yield ChatService(
                config=state.config,
                knowledge=PostgresKnowledgeRepository(session),
                memory=PostgresMemoryRepository(session),
                settings_repo=PostgresSettingsRepository(session),
                sessions=state.sessions,
                cache=state.cache,
                user_id=user_id,
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
        return
    yield ChatService(
        config=state.config,
        knowledge=FileKnowledgeRepository(state.knowledge),
        memory=FileMemoryRepository(state.memory),
        settings_repo=FileSettingsRepository(state.settings, state.config.resolved_settings_path),
        sessions=state.sessions,
        cache=state.cache,
        runtime_settings=state.settings,
        local_knowledge=state.knowledge,
        local_memory=state.memory,
    )


async def get_chat_service(
    request: Request,
    user_id: Annotated[uuid.UUID | None, Depends(get_current_user_id)] = None,
) -> AsyncIterator[ChatService]:
    async for service in _chat_service_impl(request, user_id):
        yield service

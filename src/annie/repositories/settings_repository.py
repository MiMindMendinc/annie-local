from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from annie.core.config import DEFAULT_DOCTRINE
from annie.db.models import UserSettings
from annie.env import get_settings
from annie.repositories.base import SettingsRepository


class PostgresSettingsRepository(SettingsRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _get_or_create(self, user_id: uuid.UUID) -> UserSettings:
        result = await self.session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
        row = result.scalar_one_or_none()
        settings = get_settings()
        if row:
            # Production service routes are operator-managed to prevent a user
            # setting from turning the server into an SSRF proxy.
            row.ollama_url = settings.ollama_url
            row.voice_url = settings.voice_url
            return row
        row = UserSettings(
            user_id=user_id,
            model=settings.default_model,
            ollama_url=settings.ollama_url,
            voice_url=settings.voice_url,
            temperature=0.7,
            tools_enabled=True,
            system_prompt=DEFAULT_DOCTRINE,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def load(self, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        assert user_id is not None
        row = await self._get_or_create(user_id)
        return {
            "model": row.model,
            "ollama_url": row.ollama_url,
            "voice_url": row.voice_url,
            "temperature": row.temperature,
            "tools_enabled": row.tools_enabled,
            "system_prompt": row.system_prompt,
            "default_doctrine": DEFAULT_DOCTRINE,
            "operator_managed_routes": True,
        }

    async def save(self, payload: dict[str, Any], user_id: uuid.UUID | None = None) -> dict[str, Any]:
        assert user_id is not None
        row = await self._get_or_create(user_id)
        row.model = str(payload.get("model", row.model))
        row.ollama_url = get_settings().ollama_url
        row.voice_url = get_settings().voice_url
        row.temperature = float(payload.get("temperature", row.temperature))
        row.tools_enabled = bool(payload.get("tools_enabled", row.tools_enabled))
        row.system_prompt = str(payload.get("system_prompt", row.system_prompt))
        return await self.load(user_id)

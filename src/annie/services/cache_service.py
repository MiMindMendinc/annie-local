from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as redis

from annie.env import get_settings

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self, client: redis.Redis | None = None) -> None:
        self._client = client
        self._memory: dict[str, str] = {}

    @classmethod
    async def connect(cls) -> "CacheService":
        settings = get_settings()
        try:
            client = redis.from_url(settings.redis_url, decode_responses=True)
            await client.ping()
            return cls(client)
        except Exception as exc:
            logger.warning("redis unavailable, using in-process cache: %s", exc)
            return cls(None)

    async def get_json(self, key: str) -> Any | None:
        raw = await self._get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def set_json(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        await self._set(key, json.dumps(value), ttl_seconds)

    async def delete(self, key: str) -> None:
        if self._client:
            await self._client.delete(key)
        else:
            self._memory.pop(key, None)

    async def incr_with_ttl(self, key: str, ttl_seconds: int) -> int:
        if self._client:
            pipe = self._client.pipeline()
            pipe.incr(key)
            pipe.expire(key, ttl_seconds, nx=True)
            count, _ = await pipe.execute()
            return int(count)
        current = int(self._memory.get(key, "0")) + 1
        self._memory[key] = str(current)
        return current

    async def _get(self, key: str) -> str | None:
        if self._client:
            return await self._client.get(key)
        return self._memory.get(key)

    async def _set(self, key: str, value: str, ttl_seconds: int) -> None:
        if self._client:
            await self._client.set(key, value, ex=ttl_seconds)
        else:
            self._memory[key] = value

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()

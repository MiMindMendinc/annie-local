from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from redis.asyncio import Redis

from annie.env import get_settings, is_production

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self, client: Redis | None = None) -> None:
        self._client = client
        self._memory: dict[str, tuple[str, float | None]] = {}

    @classmethod
    async def connect(cls, *, required: bool = False) -> CacheService:
        if not is_production():
            return cls(None)
        try:
            import redis.asyncio as redis
        except ImportError as exc:
            if required:
                raise RuntimeError("Redis is required in production mode") from exc
            logger.warning("redis package unavailable; using in-process cache")
            return cls(None)
        settings = get_settings()
        try:
            client = redis.from_url(settings.redis_url, decode_responses=True)
            await client.ping()
            return cls(client)
        except Exception as exc:
            if required:
                raise RuntimeError("Redis is unavailable in production mode") from exc
            logger.warning("redis unavailable; using in-process cache: %s", exc)
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
        raw = await self._get(key)
        current = int(raw or "0") + 1
        existing = self._memory.get(key)
        expires_at = existing[1] if existing is not None else time.monotonic() + ttl_seconds
        self._memory[key] = (str(current), expires_at)
        return current

    async def _get(self, key: str) -> str | None:
        if self._client:
            return await self._client.get(key)
        item = self._memory.get(key)
        if item is None:
            return None
        value, expires_at = item
        if expires_at is not None and expires_at <= time.monotonic():
            self._memory.pop(key, None)
            return None
        return value

    async def _set(self, key: str, value: str, ttl_seconds: int) -> None:
        if self._client:
            await self._client.set(key, value, ex=ttl_seconds)
        else:
            self._memory[key] = (value, time.monotonic() + ttl_seconds)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

from annie.env import get_settings

T = TypeVar("T")


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    attempts: int | None = None,
    base_delay: float | None = None,
) -> T:
    settings = get_settings()
    max_attempts = attempts or settings.http_retry_attempts
    delay = base_delay or settings.http_retry_base_delay
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return await fn()
        except (httpx.HTTPError, httpx.TimeoutException, ConnectionError) as exc:
            last_exc = exc
            if attempt >= max_attempts - 1:
                break
            sleep_for = delay * (2**attempt) + random.uniform(0, 0.25)
            await asyncio.sleep(sleep_for)
    assert last_exc is not None
    raise last_exc

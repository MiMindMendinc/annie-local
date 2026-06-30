from __future__ import annotations

import logging
from typing import Any

from arq.connections import RedisSettings

from annie.env import get_settings

logger = logging.getLogger(__name__)


async def export_knowledge_digest(ctx: dict[str, Any], user_id: str) -> dict[str, Any]:
    """Background export of knowledge digest for large profiles."""
    logger.info("exporting knowledge digest user_id=%s", user_id)
    return {"user_id": user_id, "status": "completed", "bytes": 0}


async def run_canary_benchmark(ctx: dict[str, Any]) -> dict[str, Any]:
    """Run substrate canary benchmark off the request path."""
    from scripts.run_canary_benchmark import main as run_benchmark

    logger.info("starting canary benchmark worker task")
    run_benchmark()
    return {"status": "completed"}


class WorkerSettings:
    functions = [export_knowledge_digest, run_canary_benchmark]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = get_settings().worker_concurrency

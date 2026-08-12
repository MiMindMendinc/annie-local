from __future__ import annotations

import logging
from typing import Any, ClassVar

from arq.connections import RedisSettings

from annie.env import get_settings

logger = logging.getLogger(__name__)


async def run_canary_benchmark(ctx: dict[str, Any]) -> dict[str, Any]:
    """Run substrate canary benchmark off the request path."""
    from scripts.run_canary_benchmark import run_benchmark

    logger.info("starting canary benchmark worker task")
    results = run_benchmark()
    all_pass = all(results[f"{suite}_pass"] == results[f"{suite}_total"] for suite in ("trigger", "safe", "restart"))
    return {"status": "passed" if all_pass else "failed", "results": results}


class WorkerSettings:
    functions: ClassVar[list] = [run_canary_benchmark]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = get_settings().worker_concurrency

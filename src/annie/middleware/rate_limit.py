from __future__ import annotations

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

from annie.env import get_settings
from annie.services.cache_service import CacheService

EXEMPT_PATHS = {"/api/health", "/api/auth/login", "/api/auth/register", "/", "/static"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in EXEMPT_PATHS or path.startswith("/static"):
            return await call_next(request)

        cache: CacheService | None = getattr(request.app.state, "cache", None)
        if cache is None:
            return await call_next(request)

        settings = get_settings()
        client_ip = request.client.host if request.client else "unknown"
        auth = request.headers.get("authorization", "")
        subject = auth[-12:] if auth else client_ip
        key = f"rl:{subject}:{path}"
        count = await cache.incr_with_ttl(key, ttl_seconds=60)
        if count > settings.rate_limit_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="rate limit exceeded",
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, settings.rate_limit_per_minute - count))
        return response

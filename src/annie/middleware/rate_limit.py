from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from annie.env import get_settings
from annie.services.cache_service import CacheService

EXEMPT_PATHS = {"/", "/api/live"}
AUTH_PATHS = {"/api/auth/login", "/api/auth/register"}
WINDOW_SECONDS = 60


def _headers(limit: int, remaining: int) -> dict[str, str]:
    values = {
        "RateLimit-Limit": str(limit),
        "RateLimit-Remaining": str(remaining),
        "RateLimit-Reset": str(WINDOW_SECONDS),
    }
    values.update({f"X-{key}": value for key, value in values.items()})
    return values


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in EXEMPT_PATHS or path.startswith("/static/"):
            return await call_next(request)

        cache: CacheService | None = getattr(request.app.state, "cache", None)
        if cache is None:
            return await call_next(request)

        settings = get_settings()
        client_ip = request.client.host if request.client else "unknown"
        # Never key a pre-authentication limit by attacker-controlled bearer
        # text: rotating bogus tokens would create unlimited buckets.
        subject = client_ip
        is_auth = path in AUTH_PATHS
        limit = (
            settings.auth_rate_limit_per_minute
            if is_auth
            else settings.rate_limit_per_minute + settings.rate_limit_burst
        )
        route_group = "auth" if is_auth else path
        key = f"rl:{subject}:{route_group}"
        count = await cache.incr_with_ttl(key, ttl_seconds=WINDOW_SECONDS)
        remaining = max(0, limit - count)
        headers = _headers(limit, remaining)
        if count > limit:
            headers["Retry-After"] = str(WINDOW_SECONDS)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"error": "rate_limit_exceeded", "detail": "rate limit exceeded"},
                headers=headers,
            )
        response = await call_next(request)
        response.headers.update(headers)
        return response

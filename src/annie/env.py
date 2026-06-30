from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    return int(raw)


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    return float(raw)


@dataclass(frozen=True)
class AppSettings:
    """Environment-driven production settings."""

    mode: str  # local | production
    host: str
    port: int
    log_level: str
    cors_origins: tuple[str, ...]
    jwt_secret: str
    jwt_algorithm: str
    jwt_expire_minutes: int
    auth_disabled: bool
    database_url: str
    redis_url: str
    rate_limit_per_minute: int
    rate_limit_burst: int
    s3_endpoint: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str
    s3_region: str
    s3_use_ssl: bool
    ollama_url: str
    voice_url: str
    default_model: str
    worker_concurrency: int
    http_retry_attempts: int
    http_retry_base_delay: float


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    origins = os.getenv("CORS_ORIGINS", "http://127.0.0.1:8787,http://localhost:8787")
    return AppSettings(
        mode=os.getenv("ANNIE_MODE", "local").strip().lower(),
        host=os.getenv("ANNIE_HOST", "127.0.0.1"),
        port=_int("ANNIE_PORT", 8787),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        cors_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
        jwt_secret=os.getenv("JWT_SECRET", "dev-only-change-me-in-production"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        jwt_expire_minutes=_int("JWT_EXPIRE_MINUTES", 60 * 24 * 7),
        auth_disabled=_bool("AUTH_DISABLED", True),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://annie:annie@127.0.0.1:5432/annie",
        ),
        redis_url=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
        rate_limit_per_minute=_int("RATE_LIMIT_PER_MINUTE", 120),
        rate_limit_burst=_int("RATE_LIMIT_BURST", 30),
        s3_endpoint=os.getenv("S3_ENDPOINT", "http://127.0.0.1:9000"),
        s3_access_key=os.getenv("S3_ACCESS_KEY", "annie"),
        s3_secret_key=os.getenv("S3_SECRET_KEY", "annie-secret"),
        s3_bucket=os.getenv("S3_BUCKET", "annie-uploads"),
        s3_region=os.getenv("S3_REGION", "us-east-1"),
        s3_use_ssl=_bool("S3_USE_SSL", False),
        ollama_url=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),
        voice_url=os.getenv("VOICE_URL", "http://127.0.0.1:8123"),
        default_model=os.getenv("DEFAULT_MODEL", "llama3.2"),
        worker_concurrency=_int("WORKER_CONCURRENCY", 2),
        http_retry_attempts=_int("HTTP_RETRY_ATTEMPTS", 4),
        http_retry_base_delay=_float("HTTP_RETRY_BASE_DELAY", 0.5),
    )


def is_production() -> bool:
    return get_settings().mode == "production"

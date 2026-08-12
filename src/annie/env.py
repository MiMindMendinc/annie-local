from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from ipaddress import ip_address
from urllib.parse import urlsplit

_ALLOWED_JWT_ALGORITHMS = {"HS256", "HS384", "HS512"}
_JWT_MINIMUM_BYTES = {"HS256": 32, "HS384": 48, "HS512": 64}
_DEVELOPMENT_SECRETS = {
    "dev-only-change-me-in-production",
    "change-me-to-a-long-random-secret",
}


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


def _valid_production_origin(origin: str) -> bool:
    parsed = urlsplit(origin)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path
    ):
        return False
    if parsed.scheme == "https":
        return True
    host = parsed.hostname.casefold()
    if host == "localhost":
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


@dataclass(frozen=True)
class AppSettings:
    """Environment-driven production settings."""

    mode: str  # local | production
    host: str
    port: int
    data_dir: str
    log_level: str
    cors_origins: tuple[str, ...]
    jwt_secret: str
    jwt_algorithm: str
    jwt_expire_minutes: int
    auth_disabled: bool
    registration_enabled: bool
    database_url: str
    redis_url: str
    rate_limit_per_minute: int
    rate_limit_burst: int
    auth_rate_limit_per_minute: int
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
        data_dir=os.getenv("ANNIE_DATA_DIR", "~/.annie"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        cors_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
        jwt_secret=os.getenv("JWT_SECRET", "dev-only-change-me-in-production"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        jwt_expire_minutes=_int("JWT_EXPIRE_MINUTES", 60 * 24 * 7),
        auth_disabled=_bool("AUTH_DISABLED", True),
        registration_enabled=_bool("REGISTRATION_ENABLED", False),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://annie:annie@127.0.0.1:5432/annie",
        ),
        redis_url=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
        rate_limit_per_minute=_int("RATE_LIMIT_PER_MINUTE", 120),
        rate_limit_burst=_int("RATE_LIMIT_BURST", 30),
        auth_rate_limit_per_minute=_int("AUTH_RATE_LIMIT_PER_MINUTE", 10),
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


def validate_app_settings(settings: AppSettings) -> None:
    """Reject unsafe or internally inconsistent environment configuration."""

    errors: list[str] = []
    if settings.mode not in {"local", "production"}:
        errors.append("ANNIE_MODE must be 'local' or 'production'")
    if not settings.host.strip():
        errors.append("ANNIE_HOST cannot be empty")
    if not 1 <= settings.port <= 65535:
        errors.append("ANNIE_PORT must be between 1 and 65535")
    if not settings.data_dir.strip():
        errors.append("ANNIE_DATA_DIR cannot be empty")
    if settings.jwt_algorithm not in _ALLOWED_JWT_ALGORITHMS:
        errors.append("JWT_ALGORITHM must be HS256, HS384, or HS512")
    if settings.jwt_expire_minutes <= 0:
        errors.append("JWT_EXPIRE_MINUTES must be positive")
    if settings.rate_limit_per_minute <= 0:
        errors.append("RATE_LIMIT_PER_MINUTE must be positive")
    if settings.rate_limit_burst < 0:
        errors.append("RATE_LIMIT_BURST cannot be negative")
    if settings.auth_rate_limit_per_minute <= 0:
        errors.append("AUTH_RATE_LIMIT_PER_MINUTE must be positive")
    if settings.worker_concurrency <= 0:
        errors.append("WORKER_CONCURRENCY must be positive")

    if settings.mode == "local" and not settings.auth_disabled:
        errors.append("local mode requires AUTH_DISABLED=true")

    if settings.mode == "production":
        if settings.auth_disabled:
            errors.append("production mode requires AUTH_DISABLED=false")
        minimum_secret_bytes = _JWT_MINIMUM_BYTES.get(settings.jwt_algorithm, 32)
        if (
            len(settings.jwt_secret.encode("utf-8")) < minimum_secret_bytes
            or settings.jwt_secret in _DEVELOPMENT_SECRETS
        ):
            errors.append(
                f"JWT_SECRET must be a non-default secret of at least {minimum_secret_bytes} bytes for "
                f"{settings.jwt_algorithm}"
            )
        if not settings.cors_origins or "*" in settings.cors_origins:
            errors.append("production CORS_ORIGINS must be explicit and cannot contain '*'")
        elif any(not _valid_production_origin(origin) for origin in settings.cors_origins):
            errors.append("production CORS_ORIGINS must use HTTPS, except for loopback HTTP origins")

        database = urlsplit(settings.database_url)
        if database.scheme != "postgresql+asyncpg" or not database.hostname or not database.password:
            errors.append("DATABASE_URL must be an authenticated postgresql+asyncpg URL")
        elif database.password.casefold() in {"annie", "changeme", "password"}:
            errors.append("DATABASE_URL cannot use a default database password")

        redis = urlsplit(settings.redis_url)
        if redis.scheme not in {"redis", "rediss"} or not redis.hostname or not redis.password:
            errors.append("REDIS_URL must be an authenticated redis:// or rediss:// URL")

    if errors:
        raise ValueError("invalid Annie environment: " + "; ".join(errors))


def is_production() -> bool:
    return get_settings().mode == "production"

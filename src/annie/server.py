from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from dataclasses import replace
from importlib.resources import files
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from annie import __version__
from annie.api.dependencies import AppState
from annie.api.routers import auth_router, core_router
from annie.core.config import AnnieConfig, validate_config
from annie.core.knowledge import LocalKnowledge
from annie.core.memory import LocalMemory
from annie.core.session import SessionManager
from annie.core.settings import RuntimeSettings
from annie.env import get_settings, validate_app_settings
from annie.middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    StructuredLoggingMiddleware,
    configure_cors,
    register_error_handlers,
)
from annie.middleware.security_headers import SECURE_HEADERS
from annie.services.cache_service import CacheService

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def create_app(config: AnnieConfig | None = None) -> FastAPI:
    _configure_logging()
    settings = get_settings()
    validate_app_settings(settings)
    data_root = Path(settings.data_dir).expanduser()
    config = config or AnnieConfig(
        host=settings.host,
        port=settings.port,
        model=settings.default_model,
        ollama_url=settings.ollama_url,
        voice_url=settings.voice_url,
        memory_path=str(data_root / "memory.jsonl"),
        knowledge_path=str(data_root / "knowledge.json"),
        settings_path=str(data_root / "settings.json"),
    )
    validate_config(config)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if settings.demo_lock:
            from annie.services.demo_sessions import DEMO_DOCTRINE, DemoSessionStore

            # Read only operator-selected routing. Never hydrate operator memory,
            # knowledge, sessions, or custom doctrine into a visitor's context.
            app.state.demo_settings = replace(
                RuntimeSettings.load(config.resolved_settings_path, config),
                tools_enabled=False,
                system_prompt=DEMO_DOCTRINE,
            )
            app.state.cache = CacheService()
            app.state.demo_origins = frozenset(settings.cors_origins) - {"*", "null"}
            app.state.demo_sessions = DemoSessionStore()
            reaper = asyncio.create_task(app.state.demo_sessions.reap())
            try:
                yield
            finally:
                reaper.cancel()
                with suppress(asyncio.CancelledError):
                    await reaper
                app.state.demo_sessions.close()
                await app.state.cache.close()
            return

        cache = await CacheService.connect(required=settings.mode == "production")
        memory = LocalMemory(config.resolved_memory_path)
        knowledge = LocalKnowledge(config.resolved_knowledge_path)
        sessions = SessionManager(config.resolved_root)
        runtime_settings = RuntimeSettings.load(config.resolved_settings_path, config)
        app.state.annie = AppState(
            config=config,
            cache=cache,
            memory=memory,
            knowledge=knowledge,
            sessions=sessions,
            settings=runtime_settings,
        )
        app.state.cache = cache
        if settings.mode == "production":
            from annie.db.engine import init_db

            engine, session_factory = await init_db()
            app.state.db_engine = engine
            app.state.db_session_factory = session_factory
            logger.info("production mode: postgres + redis + jwt enabled")
        else:
            logger.info("local mode: file-backed storage, auth disabled")
        yield
        await cache.close()
        if hasattr(app.state, "db_engine"):
            await app.state.db_engine.dispose()

    docs_enabled = settings.mode == "local" and not settings.demo_lock
    app = FastAPI(
        title="Annie Local",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    register_error_handlers(app)
    configure_cors(app)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(StructuredLoggingMiddleware)

    ui_path = files("annie").joinpath("ui")
    if settings.demo_lock:
        from annie.api.routers.demo import router as demo_router

        app.include_router(demo_router)

        @app.get("/static/{asset_path:path}")
        async def demo_asset(asset_path: str) -> FileResponse:
            if asset_path not in {"demo.js", "demo.css", "assets/annie-glass.webp"}:
                raise HTTPException(status_code=404, detail="Not found")
            return FileResponse(Path(str(ui_path)) / asset_path)
    else:
        app.include_router(auth_router)
        app.include_router(core_router)
        app.mount("/static", StaticFiles(directory=str(ui_path)), name="static")

    @app.get("/")
    async def index() -> FileResponse:
        if settings.demo_lock:
            return FileResponse(
                Path(str(ui_path)) / "demo.html",
                headers={
                    "Cache-Control": "no-store",
                    "Content-Security-Policy": SECURE_HEADERS["Content-Security-Policy"] + "; media-src 'self' blob:",
                },
            )
        return FileResponse(Path(str(ui_path)) / "index.html")

    return app

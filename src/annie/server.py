from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.resources import files
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from annie import __version__
from annie.api.dependencies import AppState
from annie.api.routers import auth_router, core_router
from annie.core.config import AnnieConfig
from annie.core.knowledge import LocalKnowledge
from annie.core.memory import LocalMemory
from annie.core.session import SessionManager
from annie.core.settings import RuntimeSettings
from annie.env import get_settings, is_production
from annie.middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    StructuredLoggingMiddleware,
    configure_cors,
    register_error_handlers,
)
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
    config = config or AnnieConfig(
        host=settings.host,
        port=settings.port,
        model=settings.default_model,
        ollama_url=settings.ollama_url,
        voice_url=settings.voice_url,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        cache = await CacheService.connect()
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
        if is_production():
            from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

            from annie.db.engine import init_db

            await init_db()
            engine = create_async_engine(settings.database_url, pool_pre_ping=True)
            app.state.db_engine = engine
            app.state.db_session_factory = async_sessionmaker(engine, expire_on_commit=False)
            logger.info("production mode: postgres + redis + jwt enabled")
        else:
            logger.info("local mode: file-backed storage, auth disabled")
        yield
        await cache.close()
        if hasattr(app.state, "db_engine"):
            await app.state.db_engine.dispose()

    app = FastAPI(title="Annie Local", version=__version__, lifespan=lifespan)
    register_error_handlers(app)
    configure_cors(app)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(StructuredLoggingMiddleware)

    app.include_router(auth_router)
    app.include_router(core_router)

    ui_path = files("annie").joinpath("ui")
    app.mount("/static", StaticFiles(directory=str(ui_path)), name="static")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(Path(str(ui_path)) / "index.html")

    return app

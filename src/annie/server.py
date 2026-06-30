from __future__ import annotations

from dataclasses import asdict
from importlib.resources import files
from pathlib import Path
from typing import Annotated, Any

import httpx
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from annie import __version__
from annie.core.chat import ChatEngine
from annie.core.config import AnnieConfig, DEFAULT_DOCTRINE
from annie.core.knowledge import LocalKnowledge
from annie.core.llm import LLMBackendError, OllamaBackend
from annie.core.memory import LocalMemory
from annie.core.session import SessionManager
from annie.core.settings import RuntimeSettings
from annie.core.speed_kernel import SpeedKernelAdapter
from annie.core.vision import get_vision_status
from annie.core.voice import get_voice_status, proxy_speak


class ChatRequest(BaseModel):
    message: Annotated[str, Field(min_length=1, max_length=20_000)]


class MemorySearchRequest(BaseModel):
    query: str = ""
    limit: int = Field(default=10, ge=1, le=100)


class SettingsUpdate(BaseModel):
    model: str | None = None
    ollama_url: str | None = None
    voice_url: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    tools_enabled: bool | None = None
    system_prompt: str | None = None


class SpeakRequest(BaseModel):
    text: Annotated[str, Field(min_length=1, max_length=2_000)]


class KnowledgeDeleteRequest(BaseModel):
    kind: str
    item_id: str | None = None


def create_app(config: AnnieConfig) -> FastAPI:
    app = FastAPI(title="Annie Local", version=__version__)
    memory = LocalMemory(config.resolved_memory_path)
    knowledge = LocalKnowledge(config.resolved_knowledge_path)
    sessions = SessionManager(config.resolved_root)
    settings = RuntimeSettings.load(config.resolved_settings_path, config)
    speed_kernel = SpeedKernelAdapter(enabled=config.speed_kernel, backend=config.speed_kernel_backend)

    def _llm() -> OllamaBackend:
        return OllamaBackend(settings.ollama_url, settings.model)

    def _engine() -> ChatEngine:
        return ChatEngine(
            config_model=settings.model,
            llm=_llm(),
            memory=memory,
            knowledge=knowledge,
            sessions=sessions,
            memory_path=config.resolved_memory_path,
            system_prompt=settings.system_prompt,
            temperature=settings.temperature,
            tools_enabled=settings.tools_enabled,
        )

    ui_path = files("annie").joinpath("ui")
    app.mount("/static", StaticFiles(directory=str(ui_path)), name="static")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(Path(str(ui_path)) / "index.html")

    @app.get("/api/health")
    async def health() -> dict[str, object]:
        backend_health = await _llm().health()
        voice = await get_voice_status(settings.voice_url)
        session = sessions.info()
        return {
            "ok": True,
            "app": "annie-local",
            "version": __version__,
            "backend": backend_health,
            "speed_kernel": speed_kernel.metadata(),
            "voice": asdict(voice),
            "vision": asdict(get_vision_status()),
            "session": asdict(session),
        }

    @app.get("/api/config")
    async def public_config() -> dict[str, object]:
        return config.to_public_dict()

    @app.get("/api/settings")
    async def get_settings() -> dict[str, object]:
        return settings.to_public_dict()

    @app.put("/api/settings")
    async def update_settings(request: SettingsUpdate) -> dict[str, object]:
        nonlocal settings
        settings = RuntimeSettings(
            model=request.model or settings.model,
            ollama_url=request.ollama_url or settings.ollama_url,
            voice_url=request.voice_url or settings.voice_url,
            temperature=settings.temperature if request.temperature is None else request.temperature,
            tools_enabled=settings.tools_enabled if request.tools_enabled is None else request.tools_enabled,
            system_prompt=request.system_prompt or settings.system_prompt,
        )
        settings.save(config.resolved_settings_path)
        return settings.to_public_dict()

    @app.post("/api/settings/reset-doctrine")
    async def reset_doctrine() -> dict[str, object]:
        nonlocal settings
        settings = RuntimeSettings(
            model=settings.model,
            ollama_url=settings.ollama_url,
            voice_url=settings.voice_url,
            temperature=settings.temperature,
            tools_enabled=settings.tools_enabled,
            system_prompt=DEFAULT_DOCTRINE,
        )
        settings.save(config.resolved_settings_path)
        return settings.to_public_dict()

    @app.post("/api/chat")
    async def chat(request: ChatRequest) -> dict[str, object]:
        try:
            result = await _engine().handle(request.message.strip())
        except LLMBackendError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {
            "reply": result.reply,
            "restart": result.restart,
            "tool_events": result.tool_events,
            "model": result.model,
            "speed_kernel": speed_kernel.metadata(),
            "session": asdict(sessions.info()),
        }

    @app.post("/api/session/restart")
    async def restart_session() -> dict[str, object]:
        payload = _engine().restart_session()
        return {"ok": True, **payload}

    @app.get("/api/knowledge")
    async def get_knowledge() -> dict[str, object]:
        return knowledge.snapshot()

    @app.delete("/api/knowledge")
    async def wipe_knowledge() -> dict[str, object]:
        knowledge.clear()
        return {"ok": True}

    @app.post("/api/knowledge/delete")
    async def delete_knowledge_item(request: KnowledgeDeleteRequest) -> dict[str, object]:
        try:
            knowledge.delete_item(request.kind, request.item_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"ok": True}

    @app.post("/api/memory/search")
    async def memory_search(request: MemorySearchRequest) -> dict[str, object]:
        matches = memory.search(request.query, limit=request.limit)
        return {"matches": [asdict(entry) for entry in matches]}

    @app.post("/api/voice/speak")
    async def speak(request: SpeakRequest) -> Response:
        clip = request.text.strip()[:420]
        try:
            audio, content_type = await proxy_speak(settings.voice_url, clip)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"voice bridge failed: {exc}") from exc
        return Response(content=audio, media_type=content_type)

    return app

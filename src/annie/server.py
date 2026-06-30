from __future__ import annotations

from dataclasses import asdict
from importlib.resources import files
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from annie import __version__
from annie.core._substrate import evaluate_output
from annie.core.config import AnnieConfig
from annie.core.llm import ChatMessage, LLMBackendError, OllamaBackend
from annie.core.memory import LocalMemory
from annie.core.speed_kernel import SpeedKernelAdapter
from annie.core.vision import get_vision_status
from annie.core.voice import get_voice_status


class ChatRequest(BaseModel):
    message: Annotated[str, Field(min_length=1, max_length=20_000)]


class MemorySearchRequest(BaseModel):
    query: str = ""
    limit: int = Field(default=10, ge=1, le=100)


def create_app(config: AnnieConfig) -> FastAPI:
    app = FastAPI(title="Annie Local", version=__version__)
    memory = LocalMemory(config.resolved_memory_path)
    llm = OllamaBackend(config.ollama_url, config.model)
    speed_kernel = SpeedKernelAdapter(enabled=config.speed_kernel, backend=config.speed_kernel_backend)

    ui_path = files("annie").joinpath("ui")
    app.mount("/static", StaticFiles(directory=str(ui_path)), name="static")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(Path(str(ui_path)) / "index.html")

    @app.get("/api/health")
    async def health() -> dict[str, object]:
        backend_health = await llm.health()
        return {
            "ok": True,
            "app": "annie-local",
            "version": __version__,
            "backend": backend_health,
            "speed_kernel": speed_kernel.metadata(),
            "voice": asdict(get_voice_status()),
            "vision": asdict(get_vision_status()),
        }

    @app.get("/api/config")
    async def public_config() -> dict[str, object]:
        return config.to_public_dict()

    @app.post("/api/chat")
    async def chat(request: ChatRequest) -> dict[str, object]:
        user_text = request.message.strip()
        memory.append("user", user_text)
        recent = memory.read_recent(limit=12)
        messages = [ChatMessage(role="system", content=config.system_prompt)]
        for entry in recent:
            if entry.role in {"user", "assistant"}:
                messages.append(ChatMessage(role=entry.role, content=entry.content))

        try:
            reply = await llm.chat(messages)
        except LLMBackendError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        outcome = evaluate_output(
            reply,
            memory_path=config.resolved_memory_path,
            user_text=user_text,
        )
        if outcome.triggered:
            memory.clear()
            return {
                "reply": outcome.reply,
                "restart": True,
                "model": config.model,
                "speed_kernel": speed_kernel.metadata(),
            }

        memory.append("assistant", reply)
        return {
            "reply": reply,
            "restart": False,
            "model": config.model,
            "speed_kernel": speed_kernel.metadata(),
        }

    @app.post("/api/memory/search")
    async def memory_search(request: MemorySearchRequest) -> dict[str, object]:
        matches = memory.search(request.query, limit=request.limit)
        return {"matches": [asdict(entry) for entry in matches]}

    return app

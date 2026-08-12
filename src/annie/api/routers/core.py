from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response

from annie import __version__
from annie.api.dependencies import AppState, get_chat_service, get_state
from annie.api.schemas import (
    ChatRequest,
    KnowledgeDeleteRequest,
    MemorySearchRequest,
    SettingsUpdate,
    SpeakRequest,
)
from annie.core.llm import OllamaBackend
from annie.core.runtime_status import build_runtime_status
from annie.core.speed_kernel import SpeedKernelAdapter
from annie.core.vision import get_vision_status
from annie.core.voice import get_voice_status, proxy_speak
from annie.env import get_settings as get_app_settings
from annie.services.chat_service import ChatService
from annie.utils.sanitize import sanitize_text

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health")
async def health(state: Annotated[AppState, Depends(get_state)]) -> dict:
    runtime = state.settings.to_public_dict()
    llm = OllamaBackend(runtime["ollama_url"], runtime["model"])
    backend, voice = await asyncio.gather(
        llm.health(),
        get_voice_status(runtime["voice_url"]),
    )
    app_settings = get_app_settings()
    speed_kernel = SpeedKernelAdapter(enabled=state.config.speed_kernel, backend=state.config.speed_kernel_backend)
    return {
        "ok": True,
        "app": "annie-local",
        "version": __version__,
        "backend": backend,
        "speed_kernel": speed_kernel.metadata(),
        "voice": asdict(voice),
        "vision": asdict(get_vision_status()),
        "session": asdict(state.sessions.info()),
        "runtime_status": build_runtime_status(
            mode=app_settings.mode,
            runtime=runtime,
            backend=backend,
            voice=asdict(voice),
            service_urls={
                "database": app_settings.database_url,
                "cache": app_settings.redis_url,
                "object_storage": app_settings.s3_endpoint,
            },
        ),
    }


@router.get("/config")
async def public_config(state: Annotated[AppState, Depends(get_state)]) -> dict:
    return state.config.to_public_dict()


@router.get("/settings")
async def get_settings_route(service: Annotated[ChatService, Depends(get_chat_service)]) -> dict:
    return await service.get_settings()


@router.put("/settings")
async def update_settings(
    request: SettingsUpdate,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> dict:
    return await service.update_settings(request.model_dump(exclude_none=True))


@router.post("/settings/reset-doctrine")
async def reset_doctrine(service: Annotated[ChatService, Depends(get_chat_service)]) -> dict:
    from annie.core.config import DEFAULT_DOCTRINE

    current = await service.get_settings()
    return await service.update_settings({**current, "system_prompt": DEFAULT_DOCTRINE})


@router.post("/chat")
async def chat(
    request: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> dict:
    message = sanitize_text(request.message)
    try:
        return await service.handle_message(message)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/session/restart")
async def restart_session(service: Annotated[ChatService, Depends(get_chat_service)]) -> dict:
    return await service.restart_session()


@router.get("/knowledge")
async def get_knowledge(service: Annotated[ChatService, Depends(get_chat_service)]) -> dict:
    return await service.get_knowledge()


@router.delete("/knowledge")
async def wipe_knowledge(service: Annotated[ChatService, Depends(get_chat_service)]) -> dict:
    await service.clear_knowledge()
    return {"ok": True}


@router.post("/knowledge/delete")
async def delete_knowledge_item(
    request: KnowledgeDeleteRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> dict:
    try:
        await service.delete_knowledge_item(request.kind, request.item_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/memory/search")
async def memory_search(
    request: MemorySearchRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> dict:
    matches = await service.search_memory(request.query, request.limit)
    return {"matches": matches}


@router.post("/voice/speak")
async def speak(
    request: SpeakRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> Response:
    settings = await service.get_settings()
    clip = request.text.strip()[:420]
    try:
        audio, content_type = await proxy_speak(settings["voice_url"], clip)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"voice bridge failed: {exc}") from exc
    return Response(content=audio, media_type=content_type)

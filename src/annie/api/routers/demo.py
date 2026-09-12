from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import asdict
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from annie.api.schemas import ChatRequest, SpeakRequest
from annie.core.llm import OllamaBackend
from annie.core.runtime_status import build_runtime_status
from annie.core.voice import get_voice_status, proxy_speak
from annie.services.demo_sessions import MAX_TURNS, SESSION_TTL_SECONDS, DemoSession
from annie.utils.sanitize import sanitize_text


async def demo_request(request: Request) -> None:
    """Guest APIs use explicit origins and per-page bearer tokens."""
    if request.method in {"GET", "HEAD"}:
        return
    origins = request.headers.getlist("origin")
    allowed = request.app.state.demo_origins | {str(request.base_url).rstrip("/")}
    if origins and (len(origins) != 1 or origins[0] not in allowed):
        raise HTTPException(status_code=403, detail="Use the demo on its own page.")
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(status_code=403, detail="Use the demo on its own page.")
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
        raise HTTPException(status_code=415, detail="Use application/json.")


router = APIRouter(prefix="/api", dependencies=[Depends(demo_request)])


def visitor_token(request: Request) -> str:
    values = request.headers.getlist("authorization")
    if len(values) != 1 or not values[0].startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Start a new demo conversation.")
    return values[0][7:]


async def visitor(request: Request) -> AsyncIterator[DemoSession]:
    async with request.app.state.demo_sessions.use(visitor_token(request)) as session:
        yield session


async def verify_visitor(request: Request) -> None:
    # Speech does not read or write conversation state. Authenticate it without
    # holding the conversation lock through a potentially slow voice request.
    async with request.app.state.demo_sessions.use(visitor_token(request)):
        pass


@router.get("/live")
async def live() -> dict:
    return {"ok": True}


@router.get("/settings")
async def settings(request: Request) -> dict:
    return request.app.state.demo_settings.to_guest_dict()


@router.get("/health")
async def health(request: Request) -> dict:
    runtime = request.app.state.demo_settings
    backend, voice = await asyncio.gather(
        OllamaBackend(runtime.ollama_url, runtime.model).health(), get_voice_status(runtime.voice_url)
    )
    status = build_runtime_status(mode="local", runtime=runtime.to_public_dict(), backend=backend, voice=asdict(voice))
    # Operator repair diagnostics contain model names, commands and endpoints.
    # Project only the coarse fields guests need, including for unavailable models.
    status["model"] = {key: status["model"][key] for key in ("availability", "route", "locality", "reason")} | {
        "name": "operator-managed"
    }
    status["memory"] = {
        "backend": "temporary",
        "location": "demo_host",
        "conversation_persistence": "temporary_per_visitor",
        "knowledge_tools": "disabled",
    }
    # Only the coarse runtime projection is returned, never backend payloads,
    # installed model inventories, errors, session IDs, paths, or service URLs.
    return {"ok": True, "demo_lock": True, "runtime_status": status}


@router.post("/session", status_code=201)
async def start_session(request: Request) -> dict:
    return {"token": request.app.state.demo_sessions.create(), "idle_timeout_seconds": SESSION_TTL_SECONDS}


@router.delete("/session")
async def end_session(request: Request, session: Annotated[DemoSession, Depends(visitor)]) -> dict:
    request.app.state.demo_sessions.delete(visitor_token(request))
    return {"ok": True}


@router.post("/session/restart")
async def restart_session(session: Annotated[DemoSession, Depends(visitor)]) -> dict:
    session.restart()
    return {"ok": True}


@router.post("/chat")
async def chat(payload: ChatRequest, request: Request, session: Annotated[DemoSession, Depends(visitor)]) -> dict:
    if session.turns >= MAX_TURNS:
        raise HTTPException(status_code=429, detail="This conversation has reached its limit. Start a new one.")
    session.turns += 1
    try:
        async with asyncio.timeout(125):
            result = await session.engine(request.app.state.demo_settings).handle(sanitize_text(payload.message))
    except (RuntimeError, TimeoutError) as exc:
        raise HTTPException(status_code=502, detail="The demo model could not reply. Please try again.") from exc
    finally:
        session.trim_history()
    reply = (
        "I've reset this conversation. Let's start again with a practical question." if result.restart else result.reply
    )
    return {"reply": reply, "restart": result.restart}


@router.post("/voice/speak", dependencies=[Depends(verify_visitor)])
async def speak(payload: SpeakRequest, request: Request) -> Response:
    try:
        async with asyncio.timeout(65):
            audio, content_type = await proxy_speak(
                request.app.state.demo_settings.voice_url, payload.text.strip()[:420]
            )
    except (httpx.HTTPError, TimeoutError) as exc:
        raise HTTPException(status_code=502, detail="Demo voice is unavailable.") from exc
    return Response(content=audio, media_type=content_type)

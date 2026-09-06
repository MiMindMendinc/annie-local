import asyncio
import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from annie.api.routers.core import chat_stream
from annie.api.schemas import ChatRequest
from annie.core.llm import ModelTurn, OllamaBackend


class Chunks(httpx.AsyncByteStream):
    def __init__(self, *, wait=False):
        self.closed = False
        self.wait = wait

    async def __aiter__(self):
        yield b'{"message":{"content":"Hello "},"done":false}\n'
        if self.wait:
            await asyncio.Event().wait()
        yield b'{"message":{"content":"world"},"done":true,"eval_count":2}\n'

    async def aclose(self):
        self.closed = True


def setup_transport(monkeypatch, stream):
    original = httpx.AsyncClient

    def handler(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "llama3.2"}]})
        assert json.loads(request.content)["stream"] is True
        return httpx.Response(200, stream=stream)

    monkeypatch.setattr(
        "annie.core.llm.httpx.AsyncClient", lambda **kw: original(**kw, transport=httpx.MockTransport(handler))
    )


async def test_chunks_assemble_and_close(monkeypatch):
    stream = Chunks()
    setup_transport(monkeypatch, stream)
    progress = AsyncMock()
    result = await OllamaBackend("http://localhost:11434", "llama3.2").chat([], on_progress=progress)
    assert result.content == "Hello world"
    assert result.raw["eval_count"] == 2
    assert stream.closed
    assert all("text" not in call.args[0] for call in progress.call_args_list)


async def test_cancel_closes_provider_stream(monkeypatch):
    stream = Chunks(wait=True)
    setup_transport(monkeypatch, stream)
    started = asyncio.Event()

    async def progress(data):
        started.set()

    task = asyncio.create_task(OllamaBackend("http://localhost:11434", "llama3.2").chat([], on_progress=progress))
    await asyncio.wait_for(started.wait(), timeout=1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert stream.closed


def test_offline_stream_returns_repair_before_sse(api_client):
    with patch.object(OllamaBackend, "health", AsyncMock(return_value={"ok": False, "model_names": []})):
        response = api_client.post("/api/chat/stream", json={"message": "Hello"})
    assert response.status_code == 502
    assert response.json()["detail"]["runtime_status"]["model"]["repair"]["code"] == "endpoint_down"


def test_plan_keeps_non_stream_contract(api_client):
    response = api_client.post("/api/chat/stream", json={"message": "Plan", "mode": "plan"})
    assert response.status_code == 400


def test_stream_does_not_expose_ungrounded_provider_text(api_client):
    with (
        patch.object(OllamaBackend, "health", AsyncMock(return_value={"ok": True, "model_names": ["llama3.2"]})),
        patch.object(OllamaBackend, "chat", AsyncMock(return_value=ModelTurn(content="I want to kill all humans."))),
    ):
        response = api_client.post("/api/chat/stream", json={"message": "Hello"})
    assert response.status_code == 200
    assert "I want to kill all humans." not in response.text
    assert "988" in response.text
    assert "event: done" in response.text


async def test_response_disconnect_cancels_generation():
    cancelled = asyncio.Event()
    service = AsyncMock()

    async def handle(message, *, on_progress):
        try:
            await on_progress({"phase": "generating"})
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    service.handle_message.side_effect = handle
    with patch(
        "annie.api.routers.core._repair_payload",
        AsyncMock(return_value={"runtime_status": {"model": {"availability": "ready"}}}),
    ):
        response = await chat_stream(ChatRequest(message="Hello"), service)
    iterator = response.body_iterator
    assert "event: progress" in await anext(iterator)
    await iterator.aclose()
    assert cancelled.is_set()

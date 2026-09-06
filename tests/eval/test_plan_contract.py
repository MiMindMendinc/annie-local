import importlib.util
import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from annie.core.llm import LLMBackendError, ModelTurn, OllamaBackend
from annie.core.plan import Plan, render_plan


@pytest.mark.parametrize(
    "content",
    [
        "",
        "{}",
        '{"first_action":"Act","checklist":[]}',
        '{"first_action":"' + ("a" * 241) + '","checklist":["a","b","c"]}',
        '{"first_action":"Act","checklist":["a","b",""]}',
    ],
)
def test_invalid_plan_fails_without_placeholder(content):
    with pytest.raises(LLMBackendError):
        render_plan(content)


def test_plan_contract_against_mock_ollama(api_client):
    path = Path(__file__).parents[2] / "scripts/mock_ollama.py"
    spec = importlib.util.spec_from_file_location("mock_ollama", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    server = ThreadingHTTPServer(("127.0.0.1", 0), module.OllamaDemoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        api_client.put("/api/settings", json={"ollama_url": f"http://127.0.0.1:{server.server_port}"})
        before = api_client.get("/api/knowledge").json()
        result = api_client.post("/api/chat", json={"message": "Direction: plan my next action", "mode": "plan"})
        assert result.status_code == 200
        reply = result.json()["reply"]
        assert len(reply.split("\n")[0]) <= 240
        assert 3 <= len([line for line in reply.splitlines() if line.startswith("- [ ]")]) <= 7
        assert api_client.get("/api/knowledge").json() == before
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_plan_write_tool_hallucination_rejected(api_client):
    before = api_client.get("/api/knowledge").json()
    turn = ModelTurn(content="", tool_calls=[{"function": {"name": "remember", "arguments": {"fact": "Injected"}}}])
    with patch.object(OllamaBackend, "chat", AsyncMock(return_value=turn)):
        result = api_client.post("/api/chat", json={"message": "Clarity: help me think", "mode": "plan"})
    assert result.status_code == 502
    assert "attempted a write" in result.json()["detail"]
    assert api_client.get("/api/knowledge").json() == before


@pytest.mark.parametrize("supports_tools", [True, False])
def test_plan_uses_provider_schema_including_tool_fallback(api_client, monkeypatch, supports_tools):
    """A prompt-only request can return prose; the provider must receive the schema."""
    original = httpx.AsyncClient
    requests = []

    def handler(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "llama3.2:latest"}]})
        payload = json.loads(request.content)
        requests.append(payload)
        if not supports_tools and payload.get("tools"):
            return httpx.Response(400, json={"error": "This model does not support tools"})
        if payload.get("format") == Plan.model_json_schema():
            content = json.dumps({"first_action": "Clear one desk corner.", "checklist": ["Sort", "Store", "Wipe"]})
        else:
            content = "Start by clearing your desk. Then sort, store, and wipe it."
        return httpx.Response(200, json={"message": {"content": content}})

    monkeypatch.setattr(
        "annie.core.llm.httpx.AsyncClient", lambda **kw: original(**kw, transport=httpx.MockTransport(handler))
    )
    before = api_client.get("/api/knowledge").json()
    response = api_client.post("/api/chat", json={"message": "Plan my desk cleanup", "mode": "plan"})
    assert response.status_code == 200
    assert response.json()["reply"].count("- [ ]") == 3
    assert len(requests) == (1 if supports_tools else 2)
    assert all(request["format"] == Plan.model_json_schema() for request in requests)
    assert api_client.get("/api/knowledge").json() == before


def test_regular_chat_does_not_request_plan_schema(api_client, monkeypatch):
    original = httpx.AsyncClient
    requests = []

    def handler(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "llama3.2:latest"}]})
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": "Hello."}})

    monkeypatch.setattr(
        "annie.core.llm.httpx.AsyncClient", lambda **kw: original(**kw, transport=httpx.MockTransport(handler))
    )
    response = api_client.post("/api/chat", json={"message": "Hello"})
    assert response.status_code == 200
    assert response.json()["reply"] == "Hello."
    assert len(requests) == 1
    assert "format" not in requests[0]

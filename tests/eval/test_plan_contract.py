import importlib.util
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from annie.core.llm import LLMBackendError, ModelTurn, OllamaBackend
from annie.core.plan import render_plan


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

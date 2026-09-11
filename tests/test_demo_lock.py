from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from annie.core.config import AnnieConfig
from annie.core.knowledge import LocalKnowledge
from annie.core.llm import ModelTurn
from annie.core.memory import LocalMemory
from annie.core.session import SessionManager
from annie.core.settings import RuntimeSettings
from annie.core.voice import VoiceStatus
from annie.env import get_settings
from annie.server import create_app


@pytest.fixture
def demo_config(tmp_path, monkeypatch):
    monkeypatch.setenv("ANNIE_MODE", "local")
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.setenv("ANNIE_DEMO_LOCK", "true")
    get_settings.cache_clear()
    root = tmp_path / "operator"
    config = AnnieConfig(
        memory_path=str(root / "memory.jsonl"),
        knowledge_path=str(root / "knowledge.json"),
        settings_path=str(root / "settings.json"),
        system_prompt="OPERATOR_DOCTRINE operator@example.com in Exampleville",
    )
    LocalMemory(config.resolved_memory_path).append("user", "OPERATOR_CONVERSATION")
    LocalKnowledge(config.resolved_knowledge_path).remember("OPERATOR_FACT")
    SessionManager(root).restart()
    saved = RuntimeSettings.from_config(config)
    saved.system_prompt = "OPERATOR_SAVED_DOCTRINE operator@example.com in Exampleville"
    saved.save(config.resolved_settings_path)
    yield config
    get_settings.cache_clear()


@pytest.fixture
def demo_client(demo_config):
    with TestClient(create_app(demo_config), base_url="http://127.0.0.1:8787") as client:
        yield client


def start(client):
    response = client.post("/api/session", json={})
    assert response.status_code == 201
    return {"Authorization": "Bearer " + response.json()["token"]}


def files_under(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_guest_settings_are_the_only_settings_projection(demo_client):
    response = demo_client.get("/api/settings")
    assert response.status_code == 200
    assert response.json()["demo_lock"] is True
    assert response.json()["tools_enabled"] is False
    assert not {"system_prompt", "default_doctrine", "ollama_url", "voice_url"} & response.json().keys()


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/api/config", None),
        ("PUT", "/api/settings", {"temperature": 0.123}),
        ("PUT", "/api/settings/", {"tools_enabled": True}),
        ("POST", "/api/settings/reset-doctrine", {}),
        ("GET", "/api/knowledge", None),
        ("DELETE", "/api/knowledge", None),
        ("POST", "/api/knowledge", {"kind": "fact", "text": "guest write"}),
        ("PATCH", "/api/knowledge/goals/example", {"done": True}),
        ("POST", "/api/knowledge/delete", {"kind": "profile"}),
        ("POST", "/api/memory/search", {"query": "OPERATOR"}),
        ("POST", "/api/auth/register", {"email": "guest@example.com", "password": "test-password"}),
        ("GET", "/docs", None),
        ("GET", "/docs/oauth2-redirect", None),
        ("GET", "/redoc", None),
        ("GET", "/openapi.json", None),
        ("GET", "/static/index.html", None),
    ],
)
def test_operator_routes_are_not_dispatched(demo_client, demo_config, method, path, body):
    before = files_under(demo_config.resolved_root)
    response = demo_client.request(method, path, json=body, headers=start(demo_client))
    assert response.status_code in {403, 404, 405}
    assert "OPERATOR" not in response.text
    assert files_under(demo_config.resolved_root) == before


def test_chat_and_restart_require_an_issued_visitor_token(demo_client):
    for headers in ({}, {"Authorization": "Bearer made-up-token"}):
        for path in ("/api/chat", "/api/session/restart"):
            response = demo_client.post(path, json={"message": "hello"}, headers=headers)
            assert response.status_code == 401


def test_visitors_keep_separate_history_and_never_read_operator_data(demo_client, demo_config, monkeypatch):
    seen = []

    async def model(_self, messages, **kwargs):
        seen.append([m.content for m in messages])
        assert kwargs.get("tools") is None
        return ModelTurn(content="A guest reply.")

    monkeypatch.setattr("annie.core.llm.OllamaBackend.chat", model)
    before = files_under(demo_config.resolved_root)
    alice, bob = start(demo_client), start(demo_client)
    for headers, message in [(alice, "ALICE_FIRST"), (bob, "BOB_FIRST"), (alice, "ALICE_SECOND")]:
        response = demo_client.post("/api/chat", json={"message": message}, headers=headers)
        assert response.status_code == 200
        assert response.json()["reply"] == "A guest reply."
    assert "ALICE_FIRST" in seen[2]
    assert "ALICE_FIRST" not in seen[1]
    assert "BOB_FIRST" not in seen[2]
    assert "OPERATOR" not in json.dumps(seen)
    assert "operator@example.com" not in json.dumps(seen)
    assert "Michigan MindMend Inc." in seen[0][0]
    assert files_under(demo_config.resolved_root) == before
    assert demo_client.post("/api/session/restart", json={}, headers=alice).status_code == 200
    demo_client.post("/api/chat", json={"message": "AFTER_RESET"}, headers=alice)
    assert "ALICE_FIRST" not in seen[-1]
    demo_client.post("/api/chat", json={"message": "BOB_SECOND"}, headers=bob)
    assert "BOB_FIRST" in seen[-1]
    assert files_under(demo_config.resolved_root) == before


def test_demo_off_preserves_local_settings_and_memory(demo_config, monkeypatch):
    monkeypatch.setenv("ANNIE_DEMO_LOCK", "false")
    get_settings.cache_clear()
    model = AsyncMock(return_value=ModelTurn(content="Local reply."))
    monkeypatch.setattr("annie.core.llm.OllamaBackend.chat", model)
    before = json.loads(demo_config.resolved_settings_path.read_text())
    with TestClient(create_app(demo_config), base_url="http://127.0.0.1:8787") as client:
        settings = client.get("/api/settings").json()
        assert settings["system_prompt"] == before["system_prompt"]
        assert settings["tools_enabled"] is True
        assert client.get("/openapi.json").status_code == 200
        assert "OPERATOR_FACT" in client.get("/api/knowledge").text
        assert client.put("/api/settings", json={"temperature": 0.5}).status_code == 200
        assert client.post("/api/chat", json={"message": "LOCAL_NEW"}).status_code == 200
        assert "OPERATOR_CONVERSATION" in [m.content for m in model.call_args.args[0]]
        assert client.post("/api/session/restart").status_code == 200
        assert "OPERATOR_FACT" in client.get("/api/knowledge").text
    assert "OPERATOR_FACT" in demo_config.resolved_knowledge_path.read_text()


def test_demo_cannot_replace_production_auth(demo_config):
    from annie.env import validate_app_settings

    with pytest.raises(ValueError, match="ANNIE_DEMO_LOCK"):
        validate_app_settings(replace(get_settings(), mode="production"))


def test_guest_health_drops_backend_internals(demo_client, monkeypatch):
    monkeypatch.setattr(
        "annie.core.llm.OllamaBackend.health",
        AsyncMock(
            return_value={
                "ok": True,
                "model_names": ["llama3.2", "OPERATOR_MODEL"],
                "models": [{"name": "OPERATOR_MODEL", "path": "/private/model"}],
                "error": "http://operator:secret@private.example.com",
            }
        ),
    )
    monkeypatch.setattr(
        "annie.api.routers.demo.get_voice_status",
        AsyncMock(return_value=VoiceStatus(True, "http://private.example.com", True, "browser", "wopr", "SECRET_NOTE")),
    )
    response = demo_client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["runtime_status"]["model"]["availability"] == "ready"
    assert response.json()["runtime_status"]["memory"]["conversation_persistence"] == "temporary_per_visitor"
    assert response.json()["runtime_status"]["network"]["offline_verified"] is False
    for secret in ("OPERATOR", "private", "SECRET_NOTE", "llama3.2", "bridge_url", "session_id"):
        assert secret not in response.text
    assert response.headers["Cache-Control"] == "no-store"


def test_guest_never_initializes_operator_storage(demo_config):
    with (
        patch("annie.server.LocalMemory", side_effect=AssertionError("operator memory opened")),
        patch("annie.server.LocalKnowledge", side_effect=AssertionError("operator knowledge opened")),
        patch("annie.server.SessionManager", side_effect=AssertionError("operator session opened")),
        TestClient(create_app(demo_config), base_url="http://127.0.0.1:8787") as client,
    ):
        assert client.get("/api/settings").status_code == 200
        assert not hasattr(client.app.state, "annie")


@pytest.mark.parametrize("tool", ["remember", "recall", "get_datetime", "unknown"])
def test_unsolicited_model_tools_are_never_dispatched(demo_client, monkeypatch, tool):
    monkeypatch.setattr(
        "annie.core.llm.OllamaBackend.chat",
        AsyncMock(
            return_value=ModelTurn(content="", tool_calls=[{"function": {"name": tool, "arguments": {"fact": "bad"}}}])
        ),
    )
    runner = AsyncMock(side_effect=AssertionError("tool was dispatched"))
    monkeypatch.setattr("annie.core.chat.ToolRunner.run", runner)
    response = demo_client.post("/api/chat", json={"message": "Try a tool"}, headers=start(demo_client))
    assert response.status_code == 502
    assert "Try a tool" not in response.text
    runner.assert_not_called()


def test_provider_and_voice_errors_do_not_expose_routes(demo_client, monkeypatch):
    monkeypatch.setattr("annie.core.llm.OllamaBackend.chat", AsyncMock(side_effect=RuntimeError("SECRET_URL")))
    monkeypatch.setattr("annie.api.routers.demo.proxy_speak", AsyncMock(side_effect=httpx.ConnectError("SECRET_URL")))
    headers = start(demo_client)
    for path, body in (("/api/chat", {"message": "hi"}), ("/api/voice/speak", {"text": "hi"})):
        response = demo_client.post(path, json=body, headers=headers)
        assert response.status_code == 502
        assert "SECRET_URL" not in response.text


def test_expired_deleted_and_invented_tokens_never_create_sessions(demo_client):
    from fastapi import HTTPException

    store = demo_client.app.state.demo_sessions
    headers = start(demo_client)
    session = next(iter(store._sessions.values()))
    root = session.root
    session.last_used -= 1801
    store.expire()
    assert not root.exists()
    assert demo_client.post("/api/chat", json={"message": "hi"}, headers=headers).status_code == 401
    assert not store._sessions
    with pytest.raises(HTTPException):
        store._key("../operator")
    headers = start(demo_client)
    root = next(iter(store._sessions.values())).root
    assert demo_client.request("DELETE", "/api/session", json={}, headers=headers).status_code == 200
    assert not root.exists()
    assert demo_client.post("/api/chat", json={"message": "hi"}, headers=headers).status_code == 401
    assert not store._sessions


def test_shutdown_cleans_all_visitor_files(demo_config):
    with TestClient(create_app(demo_config), base_url="http://127.0.0.1:8787") as client:
        start(client)
        start(client)
        roots = [s.root for s in client.app.state.demo_sessions._sessions.values()]
        assert all(root.exists() for root in roots)
        assert all(not root.is_relative_to(demo_config.resolved_root) for root in roots)
    assert all(not root.exists() for root in roots)


def test_capacity_rejects_new_visitors_without_evicting_active_ones(demo_client):
    store = demo_client.app.state.demo_sessions
    store.max_sessions = 1
    original = start(demo_client)
    response = demo_client.post("/api/session", json={})
    assert response.status_code == 503
    assert len(store._sessions) == 1
    assert demo_client.post("/api/session/restart", json={}, headers=original).status_code == 200


@pytest.mark.asyncio
async def test_concurrent_replies_and_restarts_cannot_race(demo_config, monkeypatch):
    app = create_app(demo_config)
    entered, release = asyncio.Event(), asyncio.Event()

    async def slow_model(_self, messages, **kwargs):
        if messages[-1].content == "WAIT":
            entered.set()
            await release.wait()
        return ModelTurn(content="Reply.")

    monkeypatch.setattr("annie.core.llm.OllamaBackend.chat", slow_model)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8787") as client,
    ):
        alice, bob = [
            {"Authorization": "Bearer " + (await client.post("/api/session", json={})).json()["token"]}
            for _ in range(2)
        ]
        task = asyncio.create_task(client.post("/api/chat", json={"message": "WAIT"}, headers=alice))
        try:
            await asyncio.wait_for(entered.wait(), timeout=2)
            for path in ("/api/chat", "/api/session/restart"):
                response = await client.post(path, json={"message": "RACE"}, headers=alice)
                assert response.status_code == 409
            response = await client.request("DELETE", "/api/session", json={}, headers=alice)
            assert response.status_code == 409
            assert (await client.post("/api/chat", json={"message": "BOB"}, headers=bob)).status_code == 200
        finally:
            release.set()
            assert (await task).status_code == 200


def test_grounding_state_is_isolated_and_retained(demo_client, demo_config, monkeypatch):
    model = AsyncMock(return_value=ModelTurn(content="kill all humans"))
    monkeypatch.setattr("annie.core.llm.OllamaBackend.chat", model)
    before = files_under(demo_config.resolved_root)
    alice, bob = start(demo_client), start(demo_client)
    one = demo_client.post("/api/chat", json={"message": "first"}, headers=alice)
    two = demo_client.post("/api/chat", json={"message": "second"}, headers=alice)
    other = demo_client.post("/api/chat", json={"message": "first"}, headers=bob)
    assert one.json()["restart"] is False
    assert two.json()["restart"] is True
    assert "kill all humans" not in two.json()["reply"]
    assert "reset this conversation" in two.json()["reply"]
    assert other.json()["restart"] is False
    assert one.json()["reply"] == other.json()["reply"]
    assert files_under(demo_config.resolved_root) == before


@pytest.mark.parametrize("value", ["tru", "", "2"])
def test_invalid_demo_flag_fails_closed(monkeypatch, value):
    monkeypatch.setenv("ANNIE_DEMO_LOCK", value)
    get_settings.cache_clear()
    try:
        with pytest.raises(ValueError, match="ANNIE_DEMO_LOCK"):
            get_settings()
    finally:
        get_settings.cache_clear()


def test_cross_origin_and_form_requests_cannot_start_or_mutate_sessions(demo_client):
    for headers in (
        {"Origin": "https://foreign.example"},
        {"Origin": "null"},
        {"Sec-Fetch-Site": "cross-site"},
    ):
        assert demo_client.post("/api/session", json={}, headers=headers).status_code == 403
    assert demo_client.post("/api/session", content="{}").status_code == 415
    assert demo_client.post("/api/session", json={}, headers={"Origin": "http://127.0.0.1:8787"}).status_code == 201
    assert len(demo_client.app.state.demo_sessions._sessions) == 1


def test_demo_page_and_only_its_assets_are_available(demo_client):
    page = demo_client.get("/")
    assert page.status_code == 200
    assert "Guest demo" in page.text
    assert "settingsDialog" not in page.text
    assert "media-src 'self' blob:" in page.headers["Content-Security-Policy"]
    assert "script-src 'self';" in page.headers["Content-Security-Policy"]
    for path in ("demo.js", "demo.css", "assets/annie-glass.webp"):
        assert demo_client.get("/static/" + path).status_code == 200
    for path in ("app.js", "state.js", "../core/settings.py", "%2e%2e%2fcore%2fsettings.py"):
        assert demo_client.get("/static/" + path).status_code == 404


def test_explicit_proxy_origin_is_allowed_without_trusting_forwarded_headers(demo_config, monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://demo.example.com")
    get_settings.cache_clear()
    with TestClient(create_app(demo_config), base_url="http://127.0.0.1:8787") as client:
        assert client.post("/api/session", json={}, headers={"Origin": "https://demo.example.com"}).status_code == 201
        assert (
            client.post(
                "/api/session",
                json={},
                headers={"Origin": "https://foreign.example", "X-Forwarded-Host": "foreign.example"},
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/session",
                json={},
                headers=[("Origin", "https://demo.example.com"), ("Origin", "https://foreign.example")],
            ).status_code
            == 403
        )


def test_session_history_and_turn_count_are_bounded(demo_client, monkeypatch):
    monkeypatch.setattr("annie.core.llm.OllamaBackend.chat", AsyncMock(return_value=ModelTurn(content="Reply.")))
    headers = start(demo_client)
    for i in range(8):
        assert demo_client.post("/api/chat", json={"message": f"turn {i}"}, headers=headers).status_code == 200
    session = next(iter(demo_client.app.state.demo_sessions._sessions.values()))
    assert len(session.memory.read_recent(1000)) == 12
    session.turns = 100
    assert demo_client.post("/api/chat", json={"message": "too many"}, headers=headers).status_code == 429
    assert demo_client.post("/api/session/restart", json={}, headers=headers).status_code == 200
    assert session.turns == 0

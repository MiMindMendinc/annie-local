from __future__ import annotations

import socket
import threading
import time
from dataclasses import replace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import uvicorn
from starlette.testclient import TestClient

from annie.core.llm import ModelTurn
from annie.env import get_settings
from annie.server import create_app


@pytest.mark.parametrize("path", ["/api/knowledge", "/api/settings", "/api/config", "/api/live", "/"])
def test_foreign_host_cannot_read_local_instance(api_client, path):
    api_client.app.state.annie.knowledge.update_profile("Synthetic private profile")
    response = api_client.get(path, headers={"Host": "untrusted.example:8787"})
    assert response.status_code == 400
    assert "Synthetic private profile" not in response.text
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize("path", ["/api/session/restart", "/api/settings/reset-doctrine"])
def test_simple_cross_origin_post_cannot_change_state(api_client, path):
    state = api_client.app.state.annie
    state.memory.append("user", "Keep this synthetic conversation")
    api_client.put("/api/settings", json={"system_prompt": "Keep this synthetic instruction"})
    before = (state.memory.read_recent(), state.sessions.info(), state.settings.to_public_dict())
    # No JSON or custom header is needed by these routes; CORS preflight is absent.
    response = api_client.post(path, headers={"Origin": "https://untrusted.example"})
    assert response.status_code == 403
    assert (state.memory.read_recent(), state.sessions.info(), state.settings.to_public_dict()) == before


@pytest.mark.parametrize(
    "origin",
    ["null", "", "http://localhost:9999", "http://localhost:8787.evil.example", "https://untrusted.example"],
)
def test_untrusted_origins_cannot_mutate_knowledge_or_invoke_model(api_client, origin):
    before = api_client.get("/api/knowledge").json()
    with patch("annie.core.llm.OllamaBackend.chat", new_callable=AsyncMock) as model:
        response = api_client.post("/api/chat", json={"message": "Synthetic request"}, headers={"Origin": origin})
        assert response.status_code == 403
        model.assert_not_called()
    response = api_client.post(
        "/api/knowledge", json={"kind": "fact", "text": "Do not save"}, headers={"Origin": origin}
    )
    assert response.status_code == 403
    assert api_client.get("/api/knowledge").json() == before


@pytest.mark.parametrize(
    "host",
    [
        "",
        "localhost.evil.example",
        "127.0.0.1.evil.example",
        "localhost@evil.example",
        "localhost/ignored",
        "localhost\\ignored",
        "localhost:bad",
        "localhost:0",
        "localhost:65536",
        "localhost:8787,evil.example",
        "[::1",
        "[::1]:bad",
        "local\thost",
        "localhost?ignored",
    ],
)
def test_malformed_or_disguised_hosts_are_rejected(api_client, host):
    response = api_client.get("/api/knowledge", headers={"Host": host})
    assert response.status_code == 400


@pytest.mark.parametrize("header", ["Host", "Origin"])
def test_duplicate_security_headers_are_rejected(api_client, header):
    value = "localhost:8787" if header == "Host" else "http://localhost:8787"
    response = api_client.post("/api/session/restart", headers=[(header, value), (header, value)])
    assert response.status_code == (400 if header == "Host" else 403)


def test_forwarded_headers_do_not_grant_access(api_client):
    response = api_client.get(
        "/api/knowledge",
        headers={
            "Host": "untrusted.example",
            "X-Forwarded-Host": "localhost:8787",
            "Forwarded": 'host="localhost:8787";proto=http',
        },
    )
    assert response.status_code == 400


@pytest.mark.parametrize("host", ["127.0.0.1:8787", "localhost:8787", "LOCALHOST:8787", "[::1]:8787"])
def test_local_browser_and_cli_work_without_a_token(api_client, host):
    origin = f"http://{host.lower()}"
    response = api_client.post(
        "/api/knowledge",
        json={"kind": "goal", "text": "Keep offline goals working"},
        headers={"Host": host, "Origin": origin},
    )
    assert response.status_code == 201
    goal_id = response.json()["id"]
    assert api_client.patch(f"/api/knowledge/goals/{goal_id}", json={"done": True}).status_code == 200
    with patch("annie.core.llm.OllamaBackend.chat", new_callable=AsyncMock) as model:
        model.return_value = ModelTurn(content="Synthetic model response.")
        assert api_client.post("/api/chat", json={"message": "Hello"}, headers={"Origin": origin}).status_code == 200
    assert api_client.post("/api/session/restart", headers={"Origin": origin}).status_code == 200
    assert api_client.get("/api/knowledge").json()["goals"][0]["done"] is True


def test_custom_launch_port_uses_configured_origin(api_client):
    config = replace(api_client.app.state.annie.config, port=9797)
    with TestClient(create_app(config), base_url="http://localhost:9797") as client:
        assert client.post("/api/session/restart", headers={"Origin": "http://localhost:9797"}).status_code == 200
        assert client.post("/api/session/restart", headers={"Origin": "http://localhost:9798"}).status_code == 403


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "0:0:0:0:0:0:0:0"])
def test_wildcard_bind_does_not_authorize_arbitrary_hosts(api_client, host):
    config = replace(api_client.app.state.annie.config, host=host)
    with TestClient(create_app(config), base_url="http://localhost:8787") as client:
        assert client.get("/api/live").status_code == 200
        assert client.get("/api/knowledge", headers={"Host": "untrusted.example"}).status_code == 400
        assert client.get("/api/knowledge", headers={"Host": "[::]:8787"}).status_code == 400


def test_explicit_preview_origin_is_allowed_without_trusting_other_hosts(api_client):
    settings = replace(get_settings(), cors_origins=("http://preview.example:5173",))
    with (
        patch("annie.server.get_settings", return_value=settings),
        patch("annie.middleware.cors.get_settings", return_value=settings),
        TestClient(create_app(api_client.app.state.annie.config), base_url="http://preview.example:5173") as client,
    ):
        response = client.post("/api/session/restart", headers={"Origin": "http://preview.example:5173"})
        assert response.status_code == 200
        assert client.get("/api/knowledge", headers={"Host": "other.example"}).status_code == 400


@pytest.mark.parametrize("origin", ["*", "null", "http://localhost:8787/path", "http://user@localhost:8787"])
def test_local_origin_configuration_requires_exact_origins(api_client, origin):
    settings = replace(get_settings(), cors_origins=(origin,))
    with (
        patch("annie.server.get_settings", return_value=settings),
        pytest.raises(ValueError, match="CORS_ORIGINS"),
        TestClient(create_app(api_client.app.state.annie.config), base_url="http://localhost:8787"),
    ):
        pass


def test_authenticated_deployment_does_not_inherit_local_host_restrictions(api_client):
    settings = replace(
        get_settings(),
        mode="production",
        auth_disabled=False,
        jwt_secret="x" * 32,
        database_url="postgresql+asyncpg://annie:synthetic-password@localhost/annie",
        redis_url="redis://:synthetic-password@localhost:6379/0",
        cors_origins=("https://annie.example",),
    )
    with patch("annie.server.get_settings", return_value=settings):
        app = create_app(api_client.app.state.annie.config)
    # No lifespan: this checks routing only, without pretending PostgreSQL/Redis ran.
    client = TestClient(app, base_url="https://annie.example")
    assert client.get("/api/live").status_code == 200


def test_real_http_blocks_foreign_requests_and_preserves_offline_workspace(api_client):
    """Exercise Uvicorn over an actual loopback socket, with no model or DNS spoofing."""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        config = replace(api_client.app.state.annie.config, port=port)
        app = create_app(config)
        server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 5
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert server.started, "Uvicorn did not start"
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=2) as client:
                assert client.get("/").status_code == 200
                goal = client.post("/api/knowledge", json={"kind": "goal", "text": "Synthetic retained goal"})
                assert goal.status_code == 201
                goal_id = goal.json()["id"]
                state = app.state.annie
                state.memory.append("user", "Synthetic retained conversation")
                before = (state.memory.read_recent(), state.sessions.info())
                response = client.get("/api/knowledge", headers={"Host": f"untrusted.example:{port}"})
                assert response.status_code == 400
                assert "Synthetic retained goal" not in response.text
                response = client.post("/api/session/restart", headers={"Origin": "https://untrusted.example"})
                assert response.status_code == 403
                assert (state.memory.read_recent(), state.sessions.info()) == before
                assert client.patch(f"/api/knowledge/goals/{goal_id}", json={"done": True}).status_code == 200
                response = client.post("/api/session/restart", headers={"Origin": f"http://127.0.0.1:{port}"})
                assert response.status_code == 200
                assert not state.memory.read_recent()
                assert client.get("/api/knowledge").json()["goals"][0]["done"] is True
        finally:
            server.should_exit = True
            thread.join(timeout=5)
            assert not thread.is_alive(), "Uvicorn did not stop"

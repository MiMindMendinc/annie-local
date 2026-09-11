from __future__ import annotations

import os
import runpy
import socket
import threading
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import uvicorn
from starlette.testclient import TestClient

from annie.cli import build_parser
from annie.core.config import AnnieConfig
from annie.core.llm import ModelTurn
from annie.env import get_settings
from annie.server import create_app

REPLIT_HOST = "annie-regression.replit.dev"
REPLIT_ORIGIN = f"https://{REPLIT_HOST}"


@pytest.fixture
def launch(monkeypatch):
    for name in ("REPLIT_DEV_DOMAIN", "CORS_ORIGINS", "ANNIE_DEMO_LOCK"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ANNIE_MODE", "local")
    monkeypatch.setenv("AUTH_DISABLED", "true")
    entrypoint = runpy.run_path(str(Path(__file__).resolve().parents[1] / "main.py"))["main"]

    def capture():
        with patch("subprocess.run") as run:
            entrypoint()
        run.assert_called_once()
        assert run.call_args.kwargs["check"] is True
        return run.call_args.args[0], run.call_args.kwargs.get("env", os.environ.copy())

    get_settings.cache_clear()
    yield capture
    get_settings.cache_clear()


def test_launcher_adds_exact_https_origin_and_preserves_explicit_configuration(launch, monkeypatch):
    monkeypatch.setenv("REPLIT_DEV_DOMAIN", REPLIT_HOST)
    monkeypatch.setenv("CORS_ORIGINS", "https://operator.example,http://localhost:5173")
    monkeypatch.setenv("ANNIE_DEMO_LOCK", "true")
    before = os.environ.copy()
    command, child = launch()
    args = build_parser().parse_args(command[3:])
    assert (args.host, args.port, args.no_browser) == ("0.0.0.0", 8787, True)
    assert child["CORS_ORIGINS"].split(",") == [
        "https://operator.example",
        "http://localhost:5173",
        REPLIT_ORIGIN,
    ]
    assert child["ANNIE_DEMO_LOCK"] == "true"
    assert os.environ == before


@pytest.mark.parametrize("demo_lock", ["true", "false"])
def test_launcher_preserves_modes_and_loopback_defaults(launch, monkeypatch, demo_lock):
    monkeypatch.setenv("REPLIT_DEV_DOMAIN", REPLIT_HOST)
    monkeypatch.setenv("ANNIE_DEMO_LOCK", demo_lock)
    _, child = launch()
    assert child["ANNIE_DEMO_LOCK"] == demo_lock
    assert set(child["CORS_ORIGINS"].split(",")) == {
        "http://127.0.0.1:8787",
        "http://localhost:8787",
        REPLIT_ORIGIN,
    }


def test_launcher_without_replit_hostname_keeps_environment_unchanged(launch):
    before = os.environ.copy()
    _, child = launch()
    assert child == before


def test_launcher_deduplicates_exact_origin(launch, monkeypatch):
    monkeypatch.setenv("REPLIT_DEV_DOMAIN", REPLIT_HOST.upper())
    monkeypatch.setenv("CORS_ORIGINS", REPLIT_ORIGIN)
    _, child = launch()
    assert child["CORS_ORIGINS"] == REPLIT_ORIGIN


@pytest.mark.parametrize(
    "domain",
    [
        "",
        "*",
        "*.replit.dev",
        "https://annie.replit.dev",
        "annie.replit.dev:443",
        "user@annie.replit.dev",
        "annie.replit.dev/path",
        "annie.replit.dev?query",
        "annie.replit.dev#fragment",
        "annie.replit.dev,foreign.example",
        "annie.replit.dev\n",
        " annie.replit.dev",
        "annie..replit.dev",
        "-annie.replit.dev",
        "annie-.replit.dev",
        "annie_name.replit.dev",
        "a" * 64 + ".replit.dev",
        ".".join(["a" * 63] * 4) + ".replit.dev",
    ],
)
def test_invalid_hostname_stops_before_launch(launch, monkeypatch, domain):
    monkeypatch.setenv("REPLIT_DEV_DOMAIN", domain)
    with patch("subprocess.run") as run, pytest.raises(ValueError, match="REPLIT_DEV_DOMAIN"):
        launch()
    run.assert_not_called()


def test_replit_environment_does_not_expand_normal_local_launch(launch, monkeypatch, tmp_path):
    monkeypatch.setenv("REPLIT_DEV_DOMAIN", REPLIT_HOST)
    config = AnnieConfig(
        memory_path=str(tmp_path / "memory.jsonl"),
        knowledge_path=str(tmp_path / "knowledge.json"),
        settings_path=str(tmp_path / "settings.json"),
    )
    with TestClient(create_app(config), base_url="http://127.0.0.1:8787") as client:
        assert client.get("/").status_code == 200
        assert client.get("/", headers={"Host": REPLIT_HOST}).status_code == 400
        assert client.post("/api/session/restart", headers={"Origin": REPLIT_ORIGIN}).status_code == 403


@pytest.mark.parametrize("demo_lock", ["false", "true"])
@pytest.mark.parametrize("automatic_origin", [True, False], ids=["replit-webview", "explicit-deployment-origin"])
def test_replit_http_boundary_and_demo_integration(launch, monkeypatch, tmp_path, demo_lock, automatic_origin):
    """Real HTTP with the Host/Origin sent by an HTTPS reverse proxy, no Replit service claim."""
    monkeypatch.setenv("ANNIE_DEMO_LOCK", demo_lock)
    if automatic_origin:
        monkeypatch.setenv("REPLIT_DEV_DOMAIN", REPLIT_HOST)
    else:
        monkeypatch.setenv("CORS_ORIGINS", REPLIT_ORIGIN)
    command, child = launch()
    monkeypatch.setenv("CORS_ORIGINS", child.get("CORS_ORIGINS", ""))
    get_settings.cache_clear()
    args = build_parser().parse_args(command[3:])
    config = AnnieConfig(
        host=args.host,
        port=args.port,
        memory_path=str(tmp_path / "memory.jsonl"),
        knowledge_path=str(tmp_path / "knowledge.json"),
        settings_path=str(tmp_path / "settings.json"),
    )
    app = create_app(config)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, log_level="warning", proxy_headers=False))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 5
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert server.started, "Uvicorn did not start"
            with httpx.Client(
                base_url=f"http://127.0.0.1:{port}",
                headers={"Host": REPLIT_HOST, "Origin": REPLIT_ORIGIN},
                trust_env=False,
                timeout=2,
            ) as client:
                page = client.get("/")
                assert page.status_code == 200
                assert ("Guest demo" in page.text) == (demo_lock == "true")
                script = "demo.js" if demo_lock == "true" else "app.js"
                assert client.get("/static/" + script).status_code == 200
                assert client.get("/static/assets/annie-glass.webp").status_code == 200
                assert client.get("/api/live").status_code == 200

                write_path = "/api/session" if demo_lock == "true" else "/api/knowledge"
                body = {} if demo_lock == "true" else {"kind": "goal", "text": "Retained Replit goal"}
                for host in ("other.replit.dev", REPLIT_HOST + ".evil.example", "0.0.0.0"):
                    assert client.get("/", headers={"Host": host}).status_code == 400
                for origin in ("https://other.replit.dev", "null", f"http://{REPLIT_HOST}", REPLIT_ORIGIN + ":444"):
                    assert client.post(write_path, json=body, headers={"Origin": origin}).status_code == 403
                assert (
                    client.get("/", headers={"Host": "foreign.example", "X-Forwarded-Host": REPLIT_HOST}).status_code
                    == 400
                )
                assert (
                    client.post(
                        write_path,
                        json=body,
                        headers={"Origin": "https://foreign.example", "X-Forwarded-Host": REPLIT_HOST},
                    ).status_code
                    == 403
                )
                preflight = client.options(
                    write_path,
                    headers={"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"},
                )
                assert preflight.status_code == 200
                assert preflight.headers["Access-Control-Allow-Origin"] == REPLIT_ORIGIN

                if demo_lock == "true":
                    assert not app.state.demo_sessions._sessions
                    first = client.post(write_path, json=body)
                    second = client.post(write_path, json=body)
                    assert first.status_code == second.status_code == 201
                    assert first.json()["token"] != second.json()["token"]
                    token = {"Authorization": "Bearer " + first.json()["token"]}
                    for path in ("/api/config", "/api/knowledge", "/docs", "/openapi.json"):
                        assert client.get(path, headers=token).status_code == 404
                    assert client.put("/api/settings", json={"tools_enabled": True}, headers=token).status_code == 405
                    assert client.post("/api/chat", json={"message": "hello"}).status_code == 401
                else:
                    assert not client.get("/api/knowledge").json()["goals"]
                    assert client.post(write_path, json=body).status_code == 201
                    assert client.put("/api/settings", json={"temperature": 0.2}).status_code == 200
                    token = {}
                with patch("annie.core.llm.OllamaBackend.chat", new_callable=AsyncMock) as model:
                    model.return_value = ModelTurn(content="Synthetic Replit response.")
                    assert client.post("/api/chat", json={"message": "hello"}, headers=token).status_code == 200
                    assert model.await_count == 1
                assert client.post("/api/session/restart", json={}, headers=token).status_code == 200
                if demo_lock == "false":
                    assert client.get("/api/knowledge").json()["goals"][0]["text"] == "Retained Replit goal"
        finally:
            server.should_exit = True
            thread.join(timeout=5)
            assert not thread.is_alive(), "Uvicorn did not stop"

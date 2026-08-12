from __future__ import annotations

from dataclasses import replace
from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient

from annie.core.config import AnnieConfig
from annie.core.llm import ModelTurn
from annie.env import get_settings
from annie.server import create_app
from annie.services.cache_service import CacheService


def test_security_headers_present(tmp_path) -> None:
    config = AnnieConfig(
        memory_path=str(tmp_path / "memory.jsonl"),
        knowledge_path=str(tmp_path / "knowledge.json"),
        settings_path=str(tmp_path / "settings.json"),
    )
    with TestClient(create_app(config)) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Cache-Control") == "no-store"
    assert "script-src 'self';" in response.headers["Content-Security-Policy"]
    assert "script-src 'self' 'unsafe-inline'" not in response.headers["Content-Security-Policy"]
    assert "Strict-Transport-Security" not in response.headers
    assert "X-Request-Id" in response.headers


def test_untrusted_request_id_is_not_reflected(tmp_path) -> None:
    config = AnnieConfig(
        memory_path=str(tmp_path / "memory.jsonl"),
        knowledge_path=str(tmp_path / "knowledge.json"),
        settings_path=str(tmp_path / "settings.json"),
    )
    supplied = "attacker-controlled-" + ("x" * 200)
    with TestClient(create_app(config)) as client:
        response = client.get("/api/live", headers={"X-Request-Id": supplied})

    assert response.status_code == 200
    assert response.headers["X-Request-Id"] != supplied
    assert len(response.headers["X-Request-Id"]) == 32


def test_rate_limit_headers(tmp_path) -> None:
    config = AnnieConfig(
        memory_path=str(tmp_path / "memory.jsonl"),
        knowledge_path=str(tmp_path / "knowledge.json"),
        settings_path=str(tmp_path / "settings.json"),
    )
    with (
        TestClient(create_app(config)) as client,
        patch("annie.core.chat.OllamaBackend.chat", new_callable=AsyncMock) as mock_chat,
    ):
        mock_chat.return_value = ModelTurn(content="ok")
        response = client.post("/api/chat", json={"message": "hi"})
    assert "X-RateLimit-Limit" in response.headers
    assert response.headers["RateLimit-Reset"] == "60"


def test_chat_sanitizes_input(tmp_path) -> None:
    config = AnnieConfig(
        memory_path=str(tmp_path / "memory.jsonl"),
        knowledge_path=str(tmp_path / "knowledge.json"),
        settings_path=str(tmp_path / "settings.json"),
    )
    with (
        TestClient(create_app(config)) as client,
        patch("annie.core.chat.OllamaBackend.chat", new_callable=AsyncMock) as mock_chat,
    ):
        mock_chat.return_value = ModelTurn(content="Hello.")
        response = client.post("/api/chat", json={"message": "<script>alert(1)</script>hello"})
    assert response.status_code == 200
    assert "<script>" not in response.json()["reply"]


def test_auth_routes_have_a_strict_shared_rate_limit(tmp_path) -> None:
    config = AnnieConfig(
        memory_path=str(tmp_path / "memory.jsonl"),
        knowledge_path=str(tmp_path / "knowledge.json"),
        settings_path=str(tmp_path / "settings.json"),
    )
    limited = replace(get_settings(), auth_rate_limit_per_minute=1)
    with (
        patch("annie.middleware.rate_limit.get_settings", return_value=limited),
        TestClient(create_app(config)) as client,
    ):
        first = client.post("/api/auth/login", json={"email": "user@example.com", "password": "password-1"})
        second = client.post("/api/auth/register", json={"email": "user@example.com", "password": "password-1"})

    assert first.status_code == 403
    assert second.status_code == 429
    assert second.headers["Retry-After"] == "60"
    assert second.json()["error"] == "rate_limit_exceeded"


def test_rotating_bogus_bearer_tokens_cannot_bypass_ip_limit(tmp_path) -> None:
    config = AnnieConfig(
        memory_path=str(tmp_path / "memory.jsonl"),
        knowledge_path=str(tmp_path / "knowledge.json"),
        settings_path=str(tmp_path / "settings.json"),
    )
    limited = replace(get_settings(), rate_limit_per_minute=1, rate_limit_burst=0)
    with (
        patch("annie.middleware.rate_limit.get_settings", return_value=limited),
        TestClient(create_app(config)) as client,
    ):
        first = client.get("/api/config", headers={"Authorization": "Bearer bogus-one"})
        second = client.get("/api/config", headers={"Authorization": "Bearer bogus-two"})

    assert first.status_code == 200
    assert second.status_code == 429


@pytest.mark.asyncio
async def test_in_process_cache_honors_ttl() -> None:
    cache = CacheService()
    clock = [100.0]
    with patch("annie.services.cache_service.time.monotonic", side_effect=lambda: clock[0]):
        assert await cache.incr_with_ttl("key", ttl_seconds=60) == 1
        clock[0] = 130.0
        assert await cache.incr_with_ttl("key", ttl_seconds=60) == 2
        clock[0] = 161.0
        assert await cache.incr_with_ttl("key", ttl_seconds=60) == 1

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from annie.core.config import AnnieConfig
from annie.core.llm import ModelTurn
from annie.server import create_app


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
    assert "X-Request-Id" in response.headers


def test_rate_limit_headers(tmp_path) -> None:
    config = AnnieConfig(
        memory_path=str(tmp_path / "memory.jsonl"),
        knowledge_path=str(tmp_path / "knowledge.json"),
        settings_path=str(tmp_path / "settings.json"),
    )
    with TestClient(create_app(config)) as client:
        with patch("annie.core.chat.OllamaBackend.chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = ModelTurn(content="ok")
            response = client.post("/api/chat", json={"message": "hi"})
    assert "X-RateLimit-Limit" in response.headers


def test_chat_sanitizes_input(tmp_path) -> None:
    config = AnnieConfig(
        memory_path=str(tmp_path / "memory.jsonl"),
        knowledge_path=str(tmp_path / "knowledge.json"),
        settings_path=str(tmp_path / "settings.json"),
    )
    with TestClient(create_app(config)) as client:
        with patch("annie.core.chat.OllamaBackend.chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = ModelTurn(content="Hello.")
            response = client.post("/api/chat", json={"message": "<script>alert(1)</script>hello"})
    assert response.status_code == 200
    assert "<script>" not in response.json()["reply"]

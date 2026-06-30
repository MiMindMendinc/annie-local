from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from annie.core.config import AnnieConfig
from annie.core.llm import ModelTurn
from annie.server import create_app


def test_index_loads() -> None:
    with TestClient(create_app(AnnieConfig())) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "ANNIE" in response.text


def test_health_endpoint() -> None:
    with TestClient(create_app(AnnieConfig())) as client:
        with patch("annie.core.llm.OllamaBackend.health", new_callable=AsyncMock) as mock_health:
            mock_health.return_value = {"ok": True, "backend": "ollama", "model_names": ["llama3.2"]}
            with patch("annie.core.voice.get_voice_status", new_callable=AsyncMock) as mock_voice:
                mock_voice.return_value = {
                    "enabled": True,
                    "bridge_url": "http://127.0.0.1:8123",
                    "bridge_ok": False,
                    "stt_engine": "browser",
                    "tts_engine": "browser",
                    "note": "test",
                }
                response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["app"] == "annie-local"


def test_settings_roundtrip(tmp_path) -> None:
    config = AnnieConfig(settings_path=str(tmp_path / "settings.json"))
    with TestClient(create_app(config)) as client:
        response = client.get("/api/settings")
        assert response.status_code == 200
        assert "model" in response.json()

        response = client.put("/api/settings", json={"temperature": 0.5})
        assert response.status_code == 200
        assert response.json()["temperature"] == 0.5


def test_knowledge_empty(tmp_path) -> None:
    config = AnnieConfig(
        knowledge_path=str(tmp_path / "knowledge.json"),
        memory_path=str(tmp_path / "memory.jsonl"),
        settings_path=str(tmp_path / "settings.json"),
    )
    with TestClient(create_app(config)) as client:
        response = client.get("/api/knowledge")
    assert response.status_code == 200
    assert response.json()["profile"] == ""


def test_chat_with_mocked_llm(tmp_path) -> None:
    config = AnnieConfig(
        memory_path=str(tmp_path / "memory.jsonl"),
        knowledge_path=str(tmp_path / "knowledge.json"),
        settings_path=str(tmp_path / "settings.json"),
    )
    with TestClient(create_app(config)) as client:
        with patch("annie.core.chat.OllamaBackend.chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = ModelTurn(content="Hello from Annie.")
            response = client.post("/api/chat", json={"message": "hi"})
    assert response.status_code == 200
    data = response.json()
    assert data["reply"] == "Hello from Annie."
    assert data["restart"] is False


def test_session_restart(tmp_path) -> None:
    config = AnnieConfig(
        memory_path=str(tmp_path / "memory.jsonl"),
        knowledge_path=str(tmp_path / "knowledge.json"),
        settings_path=str(tmp_path / "settings.json"),
    )
    with TestClient(create_app(config)) as client:
        response = client.post("/api/session/restart")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert "epoch" in response.json()

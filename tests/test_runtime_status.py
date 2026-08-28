from __future__ import annotations

from annie.core.runtime_status import (
    build_runtime_status,
    classify_endpoint,
    trust_environment_proxy,
)
from annie.core.voice import get_voice_status


class _VoiceHealthResponse:
    status_code = 200

    def __init__(self, payload: object) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self.payload


class _VoiceHealthClient:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def get(self, _url: str) -> _VoiceHealthResponse:
        return _VoiceHealthResponse(self.payload)


def test_endpoint_classification_is_conservative() -> None:
    assert classify_endpoint("http://127.0.0.1:11434") == "loopback"
    assert classify_endpoint("http://[::1]:11434") == "loopback"
    assert classify_endpoint("http://ollama:11434") == "container"
    assert classify_endpoint("http://host.docker.internal:8123") == "host"
    assert classify_endpoint("http://192.168.1.4:11434") == "lan"
    assert classify_endpoint("https://models.example.com") == "remote"
    assert classify_endpoint("not a url") == "unknown"
    assert trust_environment_proxy("http://127.0.0.1:11434") is False
    assert trust_environment_proxy("http://ollama:11434") is False
    assert trust_environment_proxy("https://models.example.com") is True


async def test_voice_status_rejects_non_wopr_health_payload(monkeypatch) -> None:
    payload = {"ok": True, "service": "other", "local": True, "backend": "fake"}
    monkeypatch.setattr(
        "annie.core.voice.httpx.AsyncClient",
        lambda **_kwargs: _VoiceHealthClient(payload),
    )

    status = await get_voice_status("http://127.0.0.1:8123")
    assert status.bridge_ok is False
    assert status.tts_engine == "browser"
    assert "locality is unverified" in status.note


async def test_voice_status_accepts_explicit_wopr_health_payload(monkeypatch) -> None:
    payload = {"ok": True, "service": "annie-wopr", "local": True, "backend": "espeak-ng"}
    monkeypatch.setattr(
        "annie.core.voice.httpx.AsyncClient",
        lambda **_kwargs: _VoiceHealthClient(payload),
    )

    status = await get_voice_status("http://127.0.0.1:8123")
    assert status.bridge_ok is True
    assert status.tts_engine == "wopr"


def test_local_routes_do_not_claim_offline_verification() -> None:
    status = build_runtime_status(
        mode="local",
        runtime={
            "model": "llama3.2",
            "ollama_url": "http://127.0.0.1:11434",
            "voice_url": "http://127.0.0.1:8123",
            "tools_enabled": True,
        },
        backend={"ok": True, "model_names": ["llama3.2:latest"]},
        voice={"bridge_ok": True},
        service_urls={
            "database": "postgresql+asyncpg://annie:secret@127.0.0.1:5432/annie",
            "cache": "redis://127.0.0.1:6379/0",
        },
    )

    assert status["model"]["locality"] == "device"
    assert status["model"]["installed"] is True
    assert status["memory"] == {
        "backend": "jsonl",
        "location": "device",
        "conversation_persistence": "enabled",
        "knowledge_tools": "enabled",
    }
    assert status["voice"]["output"] == "local_bridge"
    assert status["network"]["claim"] == "not_verified"
    assert status["network"]["offline_verified"] is False


def test_remote_service_is_disclosed() -> None:
    status = build_runtime_status(
        mode="production",
        runtime={
            "model": "hosted-model",
            "ollama_url": "https://models.example.com",
            "voice_url": "https://voice.example.com",
            "tools_enabled": False,
        },
        backend={"ok": True},
        voice={"bridge_ok": True},
        service_urls={"database": "postgresql://user:secret@db.example.com/annie"},
    )

    assert status["model"]["locality"] == "remote"
    assert status["memory"]["location"] == "remote"
    assert status["voice"]["output"] == "remote_bridge"
    assert status["network"]["claim"] == "remote_configured"
    assert "database" in status["network"]["reason"]
    assert "secret" not in status["network"]["reason"]


def test_local_mode_ignores_inactive_production_routes() -> None:
    status = build_runtime_status(
        mode="local",
        runtime={
            "model": "llama3.2",
            "ollama_url": "http://127.0.0.1:11434",
            "voice_url": "http://127.0.0.1:8123",
        },
        backend={"ok": True, "model_names": ["llama3.2"]},
        voice={"bridge_ok": False},
        service_urls={"database": "postgresql://user:secret@db.example.com/annie"},
    )

    assert status["network"]["claim"] == "not_verified"
    assert "database" not in status["network"]["reason"]
    assert status["voice"]["output"] == "browser_managed_unverified"


def test_missing_model_and_lan_voice_are_labeled_truthfully() -> None:
    status = build_runtime_status(
        mode="local",
        runtime={
            "model": "llama3.2",
            "ollama_url": "http://127.0.0.1:11434",
            "voice_url": "http://192.168.1.4:8123",
        },
        backend={"ok": True, "model_names": ["mistral:latest"]},
        voice={"bridge_ok": True},
    )

    assert status["model"]["availability"] == "unavailable"
    assert status["model"]["endpoint_available"] is True
    assert status["model"]["installed"] is False
    assert status["voice"]["output"] == "local_network_bridge"
    assert status["network"]["claim"] == "not_verified"

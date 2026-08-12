from __future__ import annotations

from annie.core.runtime_status import (
    build_runtime_status,
    classify_endpoint,
    trust_environment_proxy,
)


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

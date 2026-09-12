from unittest.mock import AsyncMock, patch

import httpx
import pytest

from annie.core.llm import ChatMessage, LLMBackendError, OllamaBackend
from annie.core.runtime_status import build_runtime_status, match_model


@pytest.mark.parametrize(
    ("configured", "names", "resolved"),
    [
        ("llama3.2", ["llama3.2"], "llama3.2"),
        ("llama3.2", ["llama3.2:latest"], "llama3.2:latest"),
        ("llama3.2", ["registry.ollama.ai/library/llama3.2:latest"], "registry.ollama.ai/library/llama3.2:latest"),
        ("llama3.2", ["llama3.2:3b"], "llama3.2:3b"),
        ("llama3.2", ["llama3.2:1b", "llama3.2:3b"], None),
        ("llama3.2", ["llama3.1:8b"], None),
        ("llama3.2:3b", ["llama3.2:1b"], None),
        ("llama3.2", [], None),
    ],
)
def test_match(configured, names, resolved):
    result = match_model(configured, names)
    assert result["resolved_name"] == resolved
    assert result["installed"] is (resolved is not None)


def transport(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(
        "annie.core.llm.httpx.AsyncClient", lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(handler))
    )


@pytest.mark.parametrize(
    ("failure", "classification"),
    [
        (httpx.ConnectError("secret URL must not leak"), "unreachable"),
        (httpx.ReadTimeout("timeout"), "timeout"),
        (httpx.InvalidURL("wrong host URL"), "unknown"),
    ],
)
async def test_endpoint_failure(monkeypatch, failure, classification):
    def handler(request):
        raise failure

    transport(monkeypatch, handler)
    health = await OllamaBackend("http://127.0.0.1:11434", "llama3.2").health()
    assert health["ok"] is False
    assert health["error_class"] == classification
    assert health["model_names"] == []
    assert health["suggested_pull"] == "llama3.2"
    assert "secret" not in health["error"]
    runtime = build_runtime_status(mode="local", runtime={"model": "llama3.2"}, backend=health, voice={})
    assert runtime["model"]["repair"]["code"] == "endpoint_down"
    assert runtime["model"]["repair"]["title"] == "Connect your model"


@pytest.mark.parametrize(
    ("status", "body", "classification", "code"),
    [
        (404, {}, "http", "endpoint_down"),
        (200, {"models": []}, "empty_tags", "model_missing"),
        (200, {"models": [{"name": "llama3.1:8b"}]}, None, "name_mismatch"),
        (200, {"models": [{"name": "llama3.2:3b"}]}, None, "ready"),
        (200, {"models": None}, "unknown", "endpoint_down"),
    ],
)
async def test_health_contract(monkeypatch, status, body, classification, code):
    transport(monkeypatch, lambda request: httpx.Response(status, json=body))
    health = await OllamaBackend("http://127.0.0.1:11434", "llama3.2").health()
    assert health["error_class"] == classification
    runtime = build_runtime_status(
        mode="local", runtime={"model": "llama3.2", "ollama_url": health["base_url"]}, backend=health, voice={}
    )
    repair = runtime["model"]["repair"]
    assert repair["code"] == code
    assert repair["actions"][2]["command"] == "ollama pull llama3.2"
    assert "http://127.0.0.1:11434" in repair["detail"]
    assert "llama3.2" in repair["detail"]
    assert [action["id"] for action in repair["actions"]] == ["retry", "open_settings", "copy_pull"]
    assert runtime["network"]["offline_verified"] is False


async def test_chat_uses_resolved_tag(monkeypatch):
    import json

    def handler(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "llama3.2:3b"}]})
        assert json.loads(request.content)["model"] == "llama3.2:3b"
        return httpx.Response(200, json={"message": {"content": "Actual transport response"}})

    transport(monkeypatch, handler)
    result = await OllamaBackend("http://localhost:11434", "llama3.2").chat([ChatMessage("user", "hello")])
    assert result.content == "Actual transport response"


async def test_chat_does_not_guess_ambiguous_tag(monkeypatch):
    def handler(request):
        assert request.url.path == "/api/tags"
        return httpx.Response(200, json={"models": [{"name": "llama3.2:1b"}, {"name": "llama3.2:3b"}]})

    transport(monkeypatch, handler)
    with pytest.raises(LLMBackendError, match="Model unavailable"):
        await OllamaBackend("http://localhost:11434", "llama3.2").chat([])


def test_models_uses_saved_settings(api_client):
    api_client.put("/api/settings", json={"model": "llama3.1:8b"})
    with patch(
        "annie.core.llm.OllamaBackend.health", new=AsyncMock(return_value={"ok": True, "model_names": ["llama3.1:8b"]})
    ):
        response = api_client.get("/api/models")
    assert response.status_code == 200
    assert response.json()["configured_name"] == "llama3.1:8b"


def test_doctor_prints_saved_configuration_and_repair(monkeypatch, tmp_path, capsys):
    from annie import cli
    from annie.core.config import AnnieConfig
    from annie.core.settings import RuntimeSettings

    config = AnnieConfig(settings_path=str(tmp_path / "settings.json"), memory_path=str(tmp_path / "memory.jsonl"))
    runtime = RuntimeSettings.from_config(config)
    runtime.model = "llama3.1:8b"
    runtime.save(config.resolved_settings_path)
    monkeypatch.setattr(cli, "AnnieConfig", lambda: config)
    monkeypatch.setattr(cli, "_voice_bridge_online", lambda url: False)
    monkeypatch.setattr(cli.OllamaBackend, "health", AsyncMock(return_value={"ok": False, "model_names": []}))
    assert cli.run_doctor() == 1
    output = capsys.readouterr().out
    assert "configured : llama3.1:8b" in output
    assert "reachable  : NO" in output
    assert "ollama serve" in output
    assert "ollama pull llama3.1:8b" in output


@pytest.mark.parametrize("answer", ["no", "y", ""])
def test_setup_requires_explicit_yes(monkeypatch, tmp_path, answer):
    from annie import cli
    from annie.core.config import AnnieConfig

    config = AnnieConfig(settings_path=str(tmp_path / "settings.json"))
    monkeypatch.setattr(cli, "AnnieConfig", lambda: config)
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/ollama")
    monkeypatch.setattr("builtins.input", lambda prompt: answer)
    monkeypatch.setattr(
        cli.OllamaBackend, "health", AsyncMock(return_value={"ok": True, "endpoint_available": True, "model_names": []})
    )
    with patch.object(cli.subprocess, "run") as pull:
        assert cli.run_setup() == 1
        pull.assert_not_called()
    assert not config.resolved_settings_path.exists()


def test_setup_saves_only_after_verified_pull(monkeypatch, tmp_path):
    from annie import cli
    from annie.core.config import AnnieConfig

    config = AnnieConfig(settings_path=str(tmp_path / "settings.json"))
    monkeypatch.setattr(cli, "AnnieConfig", lambda: config)
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/ollama")
    monkeypatch.setattr("builtins.input", lambda prompt: "yes")
    monkeypatch.setattr(
        cli.OllamaBackend,
        "health",
        AsyncMock(
            side_effect=[
                {"ok": True, "endpoint_available": True, "model_names": []},
                {"ok": True, "installed": False, "model_names": []},
            ]
        ),
    )
    with patch.object(cli.subprocess, "run") as pull:
        pull.return_value.returncode = 0
        assert cli.run_setup() == 1
        assert pull.call_args.args[0] == ["/usr/bin/ollama", "pull", "llama3.2"]
    assert not config.resolved_settings_path.exists()

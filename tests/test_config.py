from dataclasses import replace

import pytest

from annie import cli
from annie.cli import build_parser
from annie.core.config import AnnieConfig, validate_config
from annie.core.session import SessionManager
from annie.env import get_settings, validate_app_settings
from annie.services.chat_service import validate_settings_update


def test_default_config_is_valid():
    validate_config(AnnieConfig())


def test_public_config_hides_system_prompt():
    config = AnnieConfig(model="llama3.2")
    data = config.to_public_dict()

    assert data["model"] == "llama3.2"
    assert "system_prompt" not in data


def test_speed_kernel_config_is_publicly_visible():
    config = AnnieConfig(speed_kernel=True, speed_kernel_backend="dominus-ultra")
    data = config.to_public_dict()

    assert data["speed_kernel"] is True
    assert data["speed_kernel_backend"] == "dominus-ultra"


def test_invalid_port_rejected():
    with pytest.raises(ValueError):
        validate_config(AnnieConfig(port=70000))


def test_invalid_ollama_url_rejected():
    with pytest.raises(ValueError):
        validate_config(AnnieConfig(ollama_url="localhost:11434"))


def test_invalid_speed_kernel_backend_rejected():
    with pytest.raises(ValueError):
        validate_config(AnnieConfig(speed_kernel_backend="unknown"))


def test_launch_parser_accepts_isolated_storage_paths(tmp_path):
    parser = build_parser()
    args = parser.parse_args(
        [
            "launch",
            "--memory-path",
            str(tmp_path / "memory.jsonl"),
            "--knowledge-path",
            str(tmp_path / "knowledge.json"),
            "--settings-path",
            str(tmp_path / "settings.json"),
        ]
    )

    assert args.memory_path == str(tmp_path / "memory.jsonl")
    assert args.knowledge_path == str(tmp_path / "knowledge.json")
    assert args.settings_path == str(tmp_path / "settings.json")


def test_launch_parser_enables_voice_bridge_auto_by_default() -> None:
    parser = build_parser()
    args = parser.parse_args(["launch"])
    assert args.voice_bridge == "auto"


def test_local_voice_route_detection() -> None:
    assert cli._is_local_voice_url("http://127.0.0.1:8123") is True
    assert cli._is_local_voice_url("http://localhost:8123") is True
    assert cli._is_local_voice_url("http://192.168.1.5:8123") is False


def test_launch_skips_bridge_start_for_non_local_voice_route(monkeypatch) -> None:
    called = {"health": False}

    def fake_health(url: str) -> bool:
        called["health"] = True
        return False

    monkeypatch.setattr(cli, "_voice_bridge_online", fake_health)
    assert cli._start_local_voice_bridge("http://192.168.1.5:8123") is None
    assert called["health"] is False


def _production_settings(**changes):
    settings = replace(
        get_settings(),
        mode="production",
        auth_disabled=False,
        jwt_secret="a-secure-release-secret-with-32-bytes",
        cors_origins=("https://annie.example",),
        database_url="postgresql+asyncpg://annie:strong-db-secret@postgres:5432/annie",
        redis_url="redis://:strong-redis-secret@redis:6379/0",
    )
    return replace(settings, **changes)


def test_production_environment_accepts_explicit_secrets() -> None:
    validate_app_settings(_production_settings())


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"auth_disabled": True}, "AUTH_DISABLED=false"),
        ({"jwt_secret": "short"}, "JWT_SECRET"),
        ({"jwt_algorithm": "HS512", "jwt_secret": "x" * 32}, "at least 64 bytes"),
        ({"cors_origins": ("*",)}, "CORS_ORIGINS"),
        ({"cors_origins": ("http://annie.example",)}, "must use HTTPS"),
        ({"database_url": "postgresql+asyncpg://annie:annie@postgres:5432/annie"}, "database password"),
        ({"redis_url": "redis://redis:6379/0"}, "REDIS_URL"),
    ],
)
def test_production_environment_rejects_unsafe_defaults(changes, message) -> None:
    with pytest.raises(ValueError, match=message):
        validate_app_settings(_production_settings(**changes))


def test_session_manager_hydrates_isolated_durable_state(tmp_path) -> None:
    sessions = SessionManager.from_state(
        tmp_path / "user-a",
        session_id="session-a",
        epoch=4,
        restarted_at=1234.5,
        grounding_strikes=1,
    )

    assert sessions.info().session_id == "session-a"
    assert sessions.info().epoch == 4
    assert sessions.grounding_strikes() == 1

    reloaded = SessionManager(tmp_path / "user-a")
    assert reloaded.info() == sessions.info()


def test_production_user_cannot_override_server_routes() -> None:
    with pytest.raises(ValueError, match="operator-managed"):
        validate_settings_update({"ollama_url": "http://169.254.169.254"}, production=True)


def test_local_route_update_requires_an_http_url() -> None:
    with pytest.raises(ValueError, match="valid http"):
        validate_settings_update({"voice_url": "file:///etc/passwd"}, production=False)

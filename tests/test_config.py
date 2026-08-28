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


def test_launch_parser_can_disable_voice_bridge() -> None:
    parser = build_parser()
    args = parser.parse_args(["launch", "--voice-bridge", "off"])
    assert args.voice_bridge == "off"


def test_local_voice_route_detection() -> None:
    assert cli._is_local_voice_url("http://127.0.0.1:8123") is True
    assert cli._is_local_voice_url("http://127.0.0.1") is True
    assert cli._is_local_voice_url("http://127.0.0.2:8123") is True
    assert cli._is_local_voice_url("http://[::1]:8123") is True
    assert cli._is_local_voice_url("http://localhost:8123") is True
    assert cli._is_local_voice_url("https://127.0.0.1:8123") is False
    assert cli._is_local_voice_url("http://user:pass@127.0.0.1:8123") is False
    assert cli._is_local_voice_url("http://127.0.0.1:8123/custom") is False
    assert cli._is_local_voice_url("http://192.168.1.5:8123") is False
    assert cli._is_local_voice_url("http://127.0.0.1:0") is False
    assert cli._is_local_voice_url("http://127.0.0.1:70000") is False


class _HealthResponse:
    def __init__(self, payload: object, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def json(self) -> object:
        return self.payload


def test_voice_health_requires_the_wopr_contract(monkeypatch) -> None:
    payloads = [
        {"ok": True, "service": "other-service", "local": True, "backend": "fake"},
        {"ok": True, "service": "annie-wopr", "local": False, "backend": "cloud"},
        {"ok": True, "service": "annie-wopr", "local": True, "backend": None},
    ]
    for payload in payloads:
        monkeypatch.setattr(cli.httpx, "get", lambda *args, _payload=payload, **kwargs: _HealthResponse(_payload))
        assert cli._voice_bridge_online("http://127.0.0.1:8123") is False

    valid = {"ok": True, "service": "annie-wopr", "local": True, "backend": "espeak-ng"}
    monkeypatch.setattr(cli.httpx, "get", lambda *args, **kwargs: _HealthResponse(valid))
    assert cli._voice_bridge_online("http://127.0.0.1:8123") is True


def test_launch_skips_bridge_start_for_non_local_voice_route(monkeypatch) -> None:
    called = {"health": False}

    def fake_health(url: str) -> bool:
        called["health"] = True
        return False

    monkeypatch.setattr(cli, "_voice_bridge_online", fake_health)
    assert cli._start_local_voice_bridge("http://192.168.1.5:8123") is None
    assert called["health"] is False


class _FakeProcess:
    def __init__(self, *, wait_hangs_once: bool = False) -> None:
        self.returncode: int | None = None
        self.terminated = False
        self.killed = False
        self.wait_calls = 0
        self.wait_hangs_once = wait_hangs_once

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9

    def wait(self, timeout: float | None = None) -> int:
        self.wait_calls += 1
        if self.wait_hangs_once and self.wait_calls == 1:
            raise cli.subprocess.TimeoutExpired("annie.wopr_server", timeout)
        self.returncode = self.returncode or 0
        return self.returncode


def test_voice_bridge_starts_packaged_module(monkeypatch) -> None:
    process = _FakeProcess()
    checks = iter([False, True])
    command: list[str] = []

    monkeypatch.setattr(cli, "_voice_bridge_online", lambda _url: next(checks))

    def fake_popen(args: list[str]) -> _FakeProcess:
        command.extend(args)
        return process

    monkeypatch.setattr(cli.subprocess, "Popen", fake_popen)
    started = cli._start_local_voice_bridge("http://127.0.0.1:8123")

    assert started is process
    assert command == [
        cli.sys.executable,
        "-m",
        "annie.wopr_server",
        "--host",
        "127.0.0.1",
        "--port",
        "8123",
    ]


def test_voice_bridge_uses_effective_http_port_when_omitted(monkeypatch) -> None:
    process = _FakeProcess()
    checks = iter([False, True])
    command: list[str] = []

    monkeypatch.setattr(cli, "_voice_bridge_online", lambda _url: next(checks))

    def fake_popen(args: list[str]) -> _FakeProcess:
        command.extend(args)
        return process

    monkeypatch.setattr(cli.subprocess, "Popen", fake_popen)
    started = cli._start_local_voice_bridge("http://127.0.0.1")

    assert started is process
    assert command[-2:] == ["--port", "80"]


def test_voice_bridge_spawn_failure_is_reported_cleanly(monkeypatch) -> None:
    def fail_spawn(_args: list[str]) -> _FakeProcess:
        raise OSError("private operating-system detail")

    monkeypatch.setattr(cli, "_voice_bridge_online", lambda _url: False)
    monkeypatch.setattr(cli.subprocess, "Popen", fail_spawn)

    with pytest.raises(RuntimeError, match="could not start the packaged local voice bridge"):
        cli._start_local_voice_bridge("http://127.0.0.1:8123")


def test_voice_bridge_cleanup_kills_a_hung_child() -> None:
    process = _FakeProcess(wait_hangs_once=True)
    cli._stop_voice_bridge(process, timeout=0.01)
    assert process.terminated is True
    assert process.killed is True
    assert process.wait_calls == 2


def test_voice_bridge_startup_timeout_cleans_up(monkeypatch) -> None:
    process = _FakeProcess()
    stopped: list[_FakeProcess] = []
    monotonic = iter([0.0, 9.0])

    monkeypatch.setattr(cli, "_voice_bridge_online", lambda _url: False)
    monkeypatch.setattr(cli.subprocess, "Popen", lambda _args: process)
    monkeypatch.setattr(cli.time, "monotonic", lambda: next(monotonic))
    monkeypatch.setattr(cli, "_stop_voice_bridge", lambda child: stopped.append(child))

    with pytest.raises(RuntimeError, match="did not become healthy"):
        cli._start_local_voice_bridge("http://127.0.0.1:8123")
    assert stopped == [process]


def test_launch_continues_with_truthful_browser_fallback(monkeypatch, capsys, tmp_path) -> None:
    parser = build_parser()
    args = parser.parse_args(["launch", "--no-browser", "--settings-path", str(tmp_path / "settings.json")])
    uvicorn_calls: list[tuple[object, str, int]] = []

    def unavailable(_url: str) -> None:
        raise RuntimeError("none")

    monkeypatch.setattr(cli, "create_app", lambda _config: object())
    monkeypatch.setattr(cli, "_start_local_voice_bridge", unavailable)
    monkeypatch.setattr(
        cli.uvicorn,
        "run",
        lambda app, *, host, port, log_level: uvicorn_calls.append((app, host, port)),
    )

    assert cli.run_launch(args) == 0
    assert len(uvicorn_calls) == 1
    assert "browser-managed speech (locality unverified)" in capsys.readouterr().err


def test_launch_cleans_up_the_bridge_it_started(monkeypatch, tmp_path) -> None:
    args = build_parser().parse_args(["launch", "--no-browser", "--settings-path", str(tmp_path / "settings.json")])
    process = _FakeProcess()
    stopped: list[_FakeProcess] = []

    monkeypatch.setattr(cli, "create_app", lambda _config: object())
    monkeypatch.setattr(cli, "_start_local_voice_bridge", lambda _url: process)
    monkeypatch.setattr(cli, "_stop_voice_bridge", lambda child: stopped.append(child))
    monkeypatch.setattr(cli.uvicorn, "run", lambda *args, **kwargs: None)

    assert cli.run_launch(args) == 0
    assert stopped == [process]


def test_launch_starts_voice_bridge_for_persisted_route(monkeypatch, tmp_path) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        '{"voice_url": "http://127.0.0.1:8222"}',
        encoding="utf-8",
    )
    args = build_parser().parse_args(["launch", "--no-browser", "--settings-path", str(settings_path)])
    targets: list[str] = []

    monkeypatch.setattr(cli, "create_app", lambda _config: object())
    monkeypatch.setattr(
        cli,
        "_start_local_voice_bridge",
        lambda voice_url: targets.append(voice_url),
    )
    monkeypatch.setattr(cli.uvicorn, "run", lambda *args, **kwargs: None)

    assert cli.run_launch(args) == 0
    assert targets == ["http://127.0.0.1:8222"]


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

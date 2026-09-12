from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from collections.abc import Sequence
from contextlib import suppress
from ipaddress import ip_address
from urllib.parse import urlsplit

import httpx
import uvicorn

from annie import __version__
from annie.core._substrate import verify_log
from annie.core.config import AnnieConfig, validate_config
from annie.core.grounding_audit import format_doctor_block, read_events, summary
from annie.core.llm import OllamaBackend
from annie.core.runtime_status import model_repair
from annie.core.settings import RuntimeSettings
from annie.core.voice import is_wopr_health_payload
from annie.server import create_app

BANNER = """
  ╔══════════════════════════════════════════╗
  ║   ANNIE LOCAL  ·  RESEARCH SESSION      ║
  ║   local-first · routes visible · yours  ║
  ╚══════════════════════════════════════════╝
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="annie",
        description="Annie Local — a local-first research assistant on your machine.",
    )
    parser.add_argument("--version", action="store_true", help="Show version and exit.")
    subparsers = parser.add_subparsers(dest="command")

    launch = subparsers.add_parser("launch", help="Launch the Annie Local web UI.")
    launch.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1).")
    launch.add_argument("--port", type=int, default=8787, help="Bind port (default: 8787).")
    launch.add_argument("--model", default="llama3.2", help="Ollama model name.")
    launch.add_argument("--ollama-url", default="http://127.0.0.1:11434", help="Ollama base URL.")
    launch.add_argument("--voice-url", default="http://127.0.0.1:8123", help="WOPR voice bridge URL.")
    launch.add_argument("--memory-path", default="~/.annie/memory.jsonl", help="Conversation memory path.")
    launch.add_argument("--knowledge-path", default="~/.annie/knowledge.json", help="Structured knowledge path.")
    launch.add_argument("--settings-path", default="~/.annie/settings.json", help="Runtime settings path.")
    launch.add_argument("--speed-kernel", action="store_true", help="Enable speed-kernel lab flag.")
    launch.add_argument(
        "--speed-kernel-backend",
        default="dominus-ultra",
        choices=["dominus-ultra"],
        help="Speed-kernel backend label.",
    )
    launch.add_argument("--no-browser", action="store_true", help="Do not open browser.")
    launch.add_argument(
        "--voice-bridge",
        choices=["auto", "off"],
        default="auto",
        help="Auto-start local WOPR voice bridge for local voice routes (default: auto).",
    )

    subparsers.add_parser("doctor", help="Diagnose your local stack.")
    subparsers.add_parser("setup", help="Install deps and verify the build.")

    grounding = subparsers.add_parser("grounding", help="Inspect grounding audit log (operator).")
    grounding.add_argument("--limit", type=int, default=10, help="Number of events to show.")
    grounding.add_argument("--json", action="store_true", help="Output JSON.")
    grounding.add_argument("--verify", action="store_true", help="Verify hash chain only.")

    return parser


def _check(name: str, ok: bool, detail: str = "") -> bool:
    mark = "✓" if ok else "✗"
    line = f"  {mark} {name}"
    if detail:
        line += f" — {detail}"
    print(line)
    return ok


def run_doctor() -> int:
    config = AnnieConfig()
    print(BANNER)
    print(f"  Annie Local v{__version__}\n")

    all_ok = True
    py_ok = sys.version_info >= (3, 11)
    all_ok &= _check("Python 3.11+", py_ok, f"{sys.version_info.major}.{sys.version_info.minor}")

    ollama_bin = shutil.which("ollama") is not None
    all_ok &= _check("Ollama CLI", ollama_bin, "install from https://ollama.com" if not ollama_bin else "")

    runtime = RuntimeSettings.load(config.resolved_settings_path, config)
    backend = asyncio.run(OllamaBackend(runtime.ollama_url, runtime.model).health())
    installed = bool(backend.get("installed"))
    all_ok &= installed
    repair = model_repair(runtime.model, runtime.ollama_url, backend)
    print("\nMODEL")
    print(f"  configured : {runtime.model}")
    print(f"  endpoint   : {runtime.ollama_url}")
    print(f"  reachable  : {'YES' if backend.get('endpoint_available') else 'NO'}")
    print(f"  installed  : {'YES' if installed else 'NO'}")
    if installed:
        print(f"  resolved   : {backend['resolved_name']}")
        print("  repair     : none")
    else:
        print("  repair     : ollama serve")
        print(f"               {repair['actions'][2]['command']}")
        if backend.get("model_names"):
            print(f"  installed tags: {', '.join(backend['model_names'])}")
        print("  Start serve in a separate terminal; run pull against the configured Ollama host.")
    wopr_ok = _voice_bridge_online(runtime.voice_url)
    _check("WOPR voice bridge (optional)", wopr_ok, runtime.voice_url if not wopr_ok else "online")

    data_dir = config.resolved_root
    _check("Data directory", True, str(data_dir))

    print()
    print("  ── Grounding substrate (operator) ──")
    for line in format_doctor_block(config.resolved_memory_path):
        print(line)

    print()
    print("  Session reset wipes: conversation memory (~/.annie/memory.jsonl)")
    print("  Session reset keeps: knowledge, settings, grounding log")
    print()

    if all_ok:
        print("  Ready. Run: annie launch\n")
        return 0
    print("  Resolve the checks above, then run annie doctor again.\n")
    return 1


def run_grounding(args: argparse.Namespace) -> int:
    config = AnnieConfig()
    memory_path = config.resolved_memory_path

    if args.verify:
        valid = verify_log(memory_path)
        print("chain valid" if valid else "chain INVALID")
        return 0 if valid else 1

    if args.json:
        print(json.dumps(summary(memory_path), indent=2))
        return 0

    print(BANNER)
    print("  Grounding audit log (redacted)\n")
    info = summary(memory_path)
    print(f"  Log: {info['log_path']}")
    print(f"  Chain valid: {info['chain_valid']}")
    print(f"  Total: {info['total_events']}  redirects: {info['redirects']}  restarts: {info['restarts']}")
    print()
    events = read_events(memory_path, limit=args.limit)
    if not events:
        print("  No events recorded yet.\n")
        return 0
    for event in events:
        print(
            f"  · strike={event.strike} action={event.action} level={event.level}\n"
            f"    excerpt: {event.excerpt}\n"
            f"    user: {event.user_redacted}\n"
            f"    hash: {event.hash_tail}…\n"
        )
    return 0


def run_setup() -> int:
    print(BANNER)
    binary = shutil.which("ollama")
    if not binary:
        print("Install Ollama from https://ollama.com/download, then run annie setup again.")
        return 1
    config = AnnieConfig()
    runtime = RuntimeSettings.load(config.resolved_settings_path, config)
    backend = asyncio.run(OllamaBackend(runtime.ollama_url, runtime.model).health())
    if not backend.get("endpoint_available"):
        print(f"Start Ollama at {runtime.ollama_url}: ollama serve (in a separate terminal).")
        return 1
    if not backend.get("installed"):
        print(f"Configured model: {runtime.model} at {runtime.ollama_url}")
        print(f"Installed: {', '.join(backend.get('model_names', [])) or 'none'}")
        try:
            answer = input(f"Download {runtime.model} to this Ollama endpoint? Type yes: ")
        except (EOFError, KeyboardInterrupt):
            return 1
        if answer.strip().lower() != "yes":
            print("No download or settings change made.")
            return 1
        result = subprocess.run(
            [binary, "pull", runtime.model], env={**os.environ, "OLLAMA_HOST": runtime.ollama_url}, check=False
        )
        if result.returncode:
            print("Pull failed. Settings were not changed.")
            return 1
        backend = asyncio.run(OllamaBackend(runtime.ollama_url, runtime.model).health())
    if not backend.get("installed"):
        print("Model did not resolve to one installed tag. Settings were not changed.")
        return 1
    runtime.model = backend["resolved_name"]
    runtime.save(config.resolved_settings_path)
    return run_launch(build_parser().parse_args(["launch"]))


def _voice_health_url(voice_url: str) -> str:
    base = voice_url.rstrip("/")
    return f"{base}/health"


def _local_voice_target(voice_url: str) -> tuple[str, int] | None:
    """Return the loopback bind target represented by a local voice URL."""

    try:
        parsed = urlsplit(voice_url)
        host = (parsed.hostname or "").strip().lower()
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme != "http"
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        return None
    if host != "localhost":
        try:
            if not ip_address(host).is_loopback:
                return None
        except ValueError:
            return None
    effective_port = port if port is not None else 80
    if not 1 <= effective_port <= 65535:
        return None
    return host, effective_port


def _is_local_voice_url(voice_url: str) -> bool:
    return _local_voice_target(voice_url) is not None


def _voice_bridge_online(voice_url: str) -> bool:
    try:
        response = httpx.get(_voice_health_url(voice_url), timeout=1.5, trust_env=False)
        if response.status_code != 200:
            return False
        return is_wopr_health_payload(response.json())
    except (httpx.HTTPError, TypeError, ValueError):
        return False


def _stop_voice_bridge(process: subprocess.Popen[str], *, timeout: float = 3.0) -> None:
    """Stop a child bridge, escalating to kill when graceful shutdown hangs."""

    if process.poll() is not None:
        return
    with suppress(OSError):
        process.terminate()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        with suppress(OSError):
            process.kill()
        with suppress(OSError, subprocess.TimeoutExpired):
            process.wait(timeout=timeout)
    except OSError:
        return


def _start_local_voice_bridge(voice_url: str) -> subprocess.Popen[str] | None:
    target = _local_voice_target(voice_url)
    if target is None:
        return None
    if _voice_bridge_online(voice_url):
        print(f"  → voice bridge: already online at {_voice_health_url(voice_url)}")
        return None

    host, port = target
    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "annie.wopr_server", "--host", host, "--port", str(port)],
        )
    except OSError as exc:
        raise RuntimeError("could not start the packaged local voice bridge") from exc

    deadline = time.monotonic() + 8.0
    while time.monotonic() < deadline:
        if _voice_bridge_online(voice_url):
            print(f"  → voice bridge: started at {voice_url}")
            return process
        if process.poll() is not None:
            code = process.returncode
            raise RuntimeError(
                f"local voice bridge failed to start (exit {code}). "
                "Install Piper with WOPR_PIPER_MODEL or install espeak-ng/espeak."
            )
        time.sleep(0.2)

    _stop_voice_bridge(process)
    raise RuntimeError("local voice bridge did not become healthy in time")


def run_launch(args: argparse.Namespace) -> int:
    config = AnnieConfig(
        host=args.host,
        port=args.port,
        model=args.model,
        ollama_url=args.ollama_url,
        voice_url=args.voice_url,
        memory_path=args.memory_path,
        knowledge_path=args.knowledge_path,
        settings_path=args.settings_path,
        speed_kernel=args.speed_kernel,
        speed_kernel_backend=args.speed_kernel_backend,
    )
    validate_config(config)
    runtime = RuntimeSettings.load(config.resolved_settings_path, config)
    runtime_voice_url = runtime.voice_url
    app = create_app(config)
    url = f"http://{config.host}:{config.port}"

    print(BANNER)
    print(f"  → {url}")
    print(f"  → model: {runtime.model}")
    backend = asyncio.run(OllamaBackend(runtime.ollama_url, runtime.model).health())
    if not backend.get("installed"):
        command = model_repair(runtime.model, runtime.ollama_url, backend)["actions"][2]["command"]
        print(
            f"Model unavailable ({runtime.model} @ {runtime.ollama_url}). UI will open in repair mode. Run: {command}"
        )
    print(f"  → memory: {config.resolved_memory_path}")
    print(f"  → knowledge: {config.resolved_knowledge_path}")
    print(f"  → settings: {config.resolved_settings_path}")
    if config.speed_kernel:
        print(f"  → speed kernel: {config.speed_kernel_backend}")
    print()

    voice_process: subprocess.Popen[str] | None = None
    if args.voice_bridge == "auto":
        try:
            voice_process = _start_local_voice_bridge(runtime_voice_url)
        except RuntimeError as exc:
            print(f"  Voice bridge unavailable: {exc}", file=sys.stderr)
            print("  → continuing with browser-managed speech (locality unverified)", file=sys.stderr)

    if not args.no_browser:
        with suppress(OSError, webbrowser.Error):
            webbrowser.open(url)
    try:
        uvicorn.run(app, host=config.host, port=config.port, log_level="info")
    finally:
        if voice_process:
            _stop_voice_bridge(voice_process)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        return 0
    if args.command == "doctor":
        return run_doctor()
    if args.command == "grounding":
        return run_grounding(args)
    if args.command == "setup":
        return run_setup()
    if args.command == "launch":
        return run_launch(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

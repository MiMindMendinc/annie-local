from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import uvicorn

from annie import __version__
from annie.core._substrate import verify_log
from annie.core.config import AnnieConfig, validate_config
from annie.core.grounding_audit import format_doctor_block, read_events, summary
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

    launch = subparsers.add_parser("launch", help="Launch the Annie-5 web UI.")
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

    models: list[str] = []
    try:
        response = httpx.get("http://127.0.0.1:11434/api/tags", timeout=3.0, trust_env=False)
        ollama_up = response.status_code == 200
        if ollama_up:
            data = response.json()
            models = [m["name"] for m in data.get("models", []) if m.get("name")]
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        ollama_up = False

    all_ok &= _check("Ollama daemon", ollama_up, "run: ollama serve" if not ollama_up else f"{len(models)} model(s)")
    if models:
        for name in models[:5]:
            print(f"      · {name}")
        if len(models) > 5:
            print(f"      · … and {len(models) - 5} more")

    recommended = any("llama3.2" in m or "llama3.1" in m for m in models)
    if ollama_up and models:
        _check("Tool-capable model", recommended, "llama3.2 recommended" if not recommended else "")

    try:
        voice = httpx.get("http://127.0.0.1:8123/health", timeout=2.0, trust_env=False)
        wopr_ok = voice.status_code == 200
    except httpx.HTTPError:
        wopr_ok = False
    _check("WOPR voice bridge (optional)", wopr_ok, "http://127.0.0.1:8123" if not wopr_ok else "online")

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

    if all_ok and models:
        print("  Ready. Run: annie launch\n")
        return 0
    if not ollama_up:
        print("  Fix: ollama serve && ollama pull llama3.2\n")
    elif not models:
        print("  Fix: ollama pull llama3.2\n")
    else:
        print("  Fix issues above, then: annie launch\n")
    return 1 if not all_ok else 0


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
    print("  Running install script …\n")
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    install = repo / "scripts" / "install.sh"
    if not install.exists():
        install = Path.cwd() / "scripts" / "install.sh"
    if install.exists():
        result = subprocess.run(["bash", str(install)], check=False)
        return result.returncode
    print("  install.sh not found. Try: pip install -e '.[dev]'\n")
    return 1


def _voice_health_url(voice_url: str) -> str:
    base = voice_url.rstrip("/")
    return f"{base}/health"


def _is_local_voice_url(voice_url: str) -> bool:
    try:
        host = (urlsplit(voice_url).hostname or "").strip().lower()
    except ValueError:
        return False
    return host in {"127.0.0.1", "::1", "localhost"}


def _voice_bridge_online(voice_url: str) -> bool:
    try:
        response = httpx.get(_voice_health_url(voice_url), timeout=1.5, trust_env=False)
    except httpx.HTTPError:
        return False
    return response.status_code == 200


def _wopr_script_path() -> Path:
    return Path(__file__).resolve().parents[2] / "wopr_server.py"


def _start_local_voice_bridge(voice_url: str) -> subprocess.Popen[str] | None:
    if not _is_local_voice_url(voice_url):
        return None
    if _voice_bridge_online(voice_url):
        print(f"  → voice bridge: already online at {_voice_health_url(voice_url)}")
        return None

    script = _wopr_script_path()
    if not script.is_file():
        raise RuntimeError(f"voice bridge script not found at {script}")

    parsed = urlsplit(voice_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8123
    env = {**os.environ}
    process = subprocess.Popen(
        [sys.executable, str(script), "--host", host, "--port", str(port)],
        env=env,
    )

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

    process.terminate()
    with suppress(OSError):
        process.wait(timeout=3)
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
    app = create_app(config)
    url = f"http://{config.host}:{config.port}"

    print(BANNER)
    print(f"  → {url}")
    print(f"  → model: {config.model}")
    print(f"  → memory: {config.resolved_memory_path}")
    print(f"  → knowledge: {config.resolved_knowledge_path}")
    print(f"  → settings: {config.resolved_settings_path}")
    if config.speed_kernel:
        print(f"  → speed kernel: {config.speed_kernel_backend}")
    print()

    voice_process: subprocess.Popen[str] | None = None
    if args.voice_bridge == "auto":
        try:
            voice_process = _start_local_voice_bridge(config.voice_url)
        except RuntimeError as exc:
            print(f"  Voice startup failed: {exc}", file=sys.stderr)
            return 1

    if not args.no_browser:
        with suppress(OSError, webbrowser.Error):
            webbrowser.open(url)
    try:
        uvicorn.run(app, host=config.host, port=config.port, log_level="info")
    finally:
        if voice_process and voice_process.poll() is None:
            voice_process.terminate()
            with suppress(OSError):
                voice_process.wait(timeout=3)
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

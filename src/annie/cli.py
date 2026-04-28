from __future__ import annotations

import argparse
import sys
import webbrowser
from typing import Sequence

import uvicorn

from annie import __version__
from annie.core.config import AnnieConfig, validate_config
from annie.server import create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="annie", description="Launch Annie Local.")
    parser.add_argument("--version", action="store_true", help="Show Annie Local version and exit.")
    subparsers = parser.add_subparsers(dest="command")

    launch = subparsers.add_parser("launch", help="Launch the local Annie web UI.")
    launch.add_argument("--host", default="127.0.0.1", help="Server bind host.")
    launch.add_argument("--port", type=int, default=8787, help="Server bind port.")
    launch.add_argument("--model", default="llama3.2", help="Ollama model name.")
    launch.add_argument("--ollama-url", default="http://127.0.0.1:11434", help="Ollama base URL.")
    launch.add_argument("--memory-path", default="~/.annie/memory.jsonl", help="Local JSONL memory path.")
    launch.add_argument("--no-browser", action="store_true", help="Do not open a browser automatically.")

    subparsers.add_parser("doctor", help="Print local setup guidance.")
    return parser


def run_doctor() -> int:
    print("Annie Local doctor")
    print(f"Version: {__version__}")
    print("Required local backend: Ollama")
    print("Try:")
    print("  ollama pull llama3.2")
    print("  annie launch --model llama3.2")
    return 0


def run_launch(args: argparse.Namespace) -> int:
    config = AnnieConfig(
        host=args.host,
        port=args.port,
        model=args.model,
        ollama_url=args.ollama_url,
        memory_path=args.memory_path,
    )
    validate_config(config)
    app = create_app(config)
    url = f"http://{config.host}:{config.port}"
    print(f"Starting Annie Local on {url}")
    print(f"Model: {config.model}")
    print(f"Memory: {config.resolved_memory_path}")
    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    uvicorn.run(app, host=config.host, port=config.port, log_level="info")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        return 0
    if args.command == "doctor":
        return run_doctor()
    if args.command == "launch":
        return run_launch(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

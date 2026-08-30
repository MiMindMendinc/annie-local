from __future__ import annotations

import argparse
import json
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

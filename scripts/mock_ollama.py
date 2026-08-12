#!/usr/bin/env python3
"""Small deterministic Ollama-compatible server for Research Session demos."""

from __future__ import annotations

import argparse
import json
import time
from contextlib import suppress
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

MODEL = "llama3.2"
REPLY = (
    "Research session ready. The model route is local, memory is inspectable, and performance metrics "
    "come directly from the model response."
)


class OllamaDemoHandler(BaseHTTPRequestHandler):
    server_version = "AnnieDemoOllama/1.0"

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        # The UI's Stop control intentionally aborts in-flight requests.
        with suppress(BrokenPipeError, ConnectionResetError):
            self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/api/tags":
            self._json(200, {"models": [{"name": MODEL, "model": MODEL}]})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/api/chat":
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            request = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid JSON"})
            return
        if not isinstance(request, dict):
            self._json(400, {"error": "JSON object required"})
            return

        messages = request.get("messages")
        last_content = messages[-1].get("content", "") if isinstance(messages, list) and messages else ""
        delay = float(getattr(self.server, "response_delay", 0.0))
        if "stop-test" in str(last_content):
            delay = max(delay, 1.5)
        if delay:
            time.sleep(delay)
        self._json(
            200,
            {
                "model": request.get("model") or MODEL,
                "created_at": datetime.now(UTC).isoformat(),
                "message": {"role": "assistant", "content": REPLY},
                "done": True,
                "done_reason": "stop",
                "total_duration": 1_150_000_000,
                "load_duration": 80_000_000,
                "prompt_eval_count": 24,
                "prompt_eval_duration": 140_000_000,
                "eval_count": 27,
                "eval_duration": 930_000_000,
            },
        )

    def log_message(self, pattern: str, *args: object) -> None:
        print(f"mock-ollama: {pattern % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=11434)
    parser.add_argument("--delay", type=float, default=0.0, help="Response delay in seconds.")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), OllamaDemoHandler)
    server.response_delay = max(0.0, args.delay)  # type: ignore[attr-defined]
    print(f"Deterministic Ollama demo listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

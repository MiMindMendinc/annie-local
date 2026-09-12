"""Repeat real Ollama streaming acceptance over HTTP with isolated synthetic data.

No model download and no existing Annie data changes. Optionally starts a
temporary Ollama daemon with --start-ollama and an explicit --model-store.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import platform
import socket
import subprocess
import tempfile
import threading
import time
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import httpx
import uvicorn

from annie.core.config import AnnieConfig
from annie.core.llm import OllamaBackend
from annie.env import get_settings
from annie.server import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="llama3.2")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--start-ollama", type=Path)
    parser.add_argument("--model-store", type=Path)
    parser.add_argument("--alternate-only", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if get_settings().mode != "local":
        parser.error("Run this verifier with ANNIE_MODE=local; production data must not be used")
    if args.start_ollama and (not args.model_store or args.ollama_url != "http://127.0.0.1:11434"):
        parser.error("--start-ollama requires --model-store and the default loopback URL")

    root = Path(__file__).resolve().parents[1]
    evidence = {
        "date_utc": datetime.now(UTC).isoformat(),
        "environment": {"platform": platform.platform(), "python": platform.python_version(), "cpus": os.cpu_count()},
        "method": "Real Ollama, real Uvicorn HTTP/SSE, temporary synthetic memory; tools disabled for timing runs",
        "runtime_sha256": {
            path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((root / "src").rglob("*"))
            if path.is_file() and path.suffix in {".py", ".js", ".css", ".html"}
        },
        "checks": [],
    }
    original_chat = OllamaBackend.chat
    provider_times = []
    cancelled = threading.Event()

    async def observed_chat(backend, messages, **kwargs):
        observation = {"first_content": None, "completed": None}
        provider_times.append(observation)
        callback = kwargs.get("on_content")

        async def content(text):
            if observation["first_content"] is None:
                observation["first_content"] = time.perf_counter()
            if callback is not None:
                await callback(text)

        if callback is not None:
            kwargs["on_content"] = content
        try:
            result = await original_chat(backend, messages, **kwargs)
            observation["completed"] = time.perf_counter()
            return result
        except asyncio.CancelledError:
            cancelled.set()
            raise

    try:
        with ExitStack() as stack:
            temporary = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="annie-stream-qa-")))
            if args.start_ollama:
                log = stack.enter_context((temporary / "ollama.log").open("w"))
                process = subprocess.Popen(
                    [str(args.start_ollama.resolve()), "serve"],
                    env={
                        **os.environ,
                        "OLLAMA_HOST": "127.0.0.1:11434",
                        "OLLAMA_MODELS": str(args.model_store.resolve()),
                        "OLLAMA_NO_CLOUD": "1",
                    },
                    stdout=log,
                    stderr=log,
                )

                def stop_model():
                    process.terminate()
                    process.wait(timeout=15)

                stack.callback(stop_model)
            client = stack.enter_context(httpx.Client(timeout=180, trust_env=False))
            for attempt in range(100):
                try:
                    version = client.get(args.ollama_url + "/api/version")
                    version.raise_for_status()
                    break
                except httpx.HTTPError:
                    if attempt == 99:
                        raise
                    time.sleep(0.1)
            evidence["ollama"] = version.json()
            inventory = client.get(args.ollama_url + "/api/tags").json()
            evidence["inventory"] = inventory
            if args.alternate_only:
                assert [m["name"] for m in inventory["models"]] == ["llama3.1:8b"], inventory
                assert args.model == "llama3.1:8b"
            memory = temporary / "memory.jsonl"
            app = create_app(
                AnnieConfig(
                    model="llama3.2" if args.alternate_only else args.model,
                    ollama_url=args.ollama_url,
                    memory_path=str(memory),
                    knowledge_path=str(temporary / "knowledge.json"),
                    settings_path=str(temporary / "settings.json"),
                )
            )
            sock = stack.enter_context(socket.socket())
            sock.bind(("127.0.0.1", 0))
            address = f"http://127.0.0.1:{sock.getsockname()[1]}"
            server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
            stack.enter_context(patch.object(OllamaBackend, "chat", observed_chat))
            thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
            thread.start()

            def stop_app():
                server.should_exit = True
                thread.join(timeout=15)
                assert not thread.is_alive(), "Test server did not stop"

            stack.callback(stop_app)
            for _attempt in range(100):
                if server.started:
                    break
                time.sleep(0.05)
            assert server.started
            if args.alternate_only:
                health = client.get(address + "/api/health").json()
                assert health["runtime_status"]["model"]["availability"] == "unavailable"
                assert health["runtime_status"]["model"]["repair"]["code"] == "name_mismatch"
                evidence["alternate_before"] = health["runtime_status"]["model"]
                client.put(address + "/api/settings", json={"model": args.model}).raise_for_status()
                ready = client.get(address + "/api/health").json()["runtime_status"]["model"]
                assert ready["availability"] == "ready"
                evidence["alternate_after"] = ready
                evidence["checks"].append({"name": "exclusive alternate model recovery via API", "pass": True})
            client.put(address + "/api/settings", json={"tools_enabled": False, "temperature": 0}).raise_for_status()

            def stream(message, stop_after_delta=False):
                provider_times.clear()
                cancelled.clear()
                started = time.perf_counter()
                received = []
                event = ""
                with client.stream("POST", address + "/api/chat/stream", json={"message": message}) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if line.startswith("event: "):
                            event = line[7:]
                        elif line.startswith("data: "):
                            row = {"event": event, "at": time.perf_counter(), "data": json.loads(line[6:])}
                            received.append(row)
                            assert event != "error", row
                            if stop_after_delta and event == "delta":
                                break
                deltas = [row for row in received if row["event"] == "delta" and row["data"].get("text", "").strip()]
                assert deltas, "No nonempty text delta"
                first = deltas[0]
                result = {
                    "first_text_ms": round((first["at"] - started) * 1000, 2),
                    "first_text": first["data"]["text"],
                    "text_events": len(deltas),
                }
                if stop_after_delta:
                    assert cancelled.wait(5), "Provider task did not cancel after HTTP disconnect"
                    result["provider_cancelled"] = True
                    return result
                done = [row for row in received if row["event"] == "done"]
                assert len(done) == 1
                completed = provider_times[-1]["completed"]
                first_provider = provider_times[0]["first_content"]
                assert first_provider is not None and completed is not None
                assert first_provider <= first["at"] < completed <= done[0]["at"]
                assert "".join(row["data"]["text"] for row in deltas).strip() == done[0]["data"]["reply"].strip()
                result.update(
                    first_provider_content_ms=round((first_provider - started) * 1000, 2),
                    provider_to_first_text_ms=round((first["at"] - first_provider) * 1000, 2),
                    provider_complete_ms=round((completed - started) * 1000, 2),
                    done_ms=round((done[0]["at"] - started) * 1000, 2),
                    reply=done[0]["data"]["reply"],
                    first_text_before_provider_complete=True,
                )
                return result

            prompt = "Start with Hello. Explain in three short sentences how to organize a desk."
            for name in ("cold streaming", "warm streaming"):
                result = stream(prompt)
                evidence["checks"].append({"name": name, "pass": True, **result})
                print(json.dumps({"name": name, **result}), flush=True)
            before_cancel = memory.read_text().splitlines()
            result = stream("Start with Hello. Write twenty paragraphs about organizing a desk.", True)
            after_cancel = [json.loads(line) for line in memory.read_text().splitlines()]
            assert len(after_cancel) == len(before_cancel) + 1
            assert after_cancel[-1]["role"] == "user"
            evidence["checks"].append(
                {"name": "HTTP cancellation without assistant memory commit", "pass": True, **result}
            )
            print(json.dumps(evidence["checks"][-1]), flush=True)
    except Exception as exc:
        evidence["failure"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(evidence, indent=2) + "\n")


if __name__ == "__main__":
    main()

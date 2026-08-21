from __future__ import annotations

import io
import json
import math
import struct
import sys
import threading
import unittest
import urllib.error
import urllib.request
import wave
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wopr_server import (  # noqa: E402
    BridgeError,
    BridgeState,
    EspeakBackend,
    PiperBackend,
    WOPRHTTPServer,
    is_loopback_host,
)


class RecordingBackend:
    name = "test-tone"

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.last_text: str | None = None

    def synthesize(self, text: str, output_path: Path) -> None:
        self.last_text = text
        if self.fail:
            raise BridgeError("private backend detail")
        with wave.open(str(output_path), "wb") as clip:
            clip.setnchannels(1)
            clip.setsampwidth(2)
            clip.setframerate(8000)
            frames = [
                struct.pack("<h", int(1200 * math.sin(2 * math.pi * 440 * index / 8000)))
                for index in range(800)
            ]
            clip.writeframes(b"".join(frames))


class RunningServer:
    def __init__(self, backend: RecordingBackend | None) -> None:
        self.server = WOPRHTTPServer(("127.0.0.1", 0), BridgeState(backend))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> tuple[str, RecordingBackend | None]:
        self.thread.start()
        host, port = self.server.server_address
        return f"http://{host}:{port}", self.server.state.backend

    def __exit__(self, *args: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def request_json(url: str, path: str) -> tuple[int, dict[str, object]]:
    try:
        with urllib.request.urlopen(f"{url}{path}", timeout=2) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code, json.load(exc)


def post(
    url: str,
    payload: bytes,
    *,
    content_type: str = "application/json",
) -> tuple[int, bytes, dict[str, str]]:
    request = urllib.request.Request(
        f"{url}/speak",
        data=payload,
        method="POST",
        headers={"Content-Type": content_type},
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)


class WOPRServerTests(unittest.TestCase):
    def test_health_reports_backend_without_claiming_cloud(self) -> None:
        backend = RecordingBackend()
        with RunningServer(backend) as (url, _):
            status, payload = request_json(url, "/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload["backend"], "test-tone")
        self.assertIs(payload["local"], True)

    def test_health_is_unavailable_without_backend(self) -> None:
        with RunningServer(None) as (url, _):
            status, payload = request_json(url, "/health")
        self.assertEqual(status, 503)
        self.assertIs(payload["ok"], False)

    def test_speak_returns_valid_wav_and_normalizes_text(self) -> None:
        backend = RecordingBackend()
        with RunningServer(backend) as (url, _):
            status, body, headers = post(url, json.dumps({"text": " hello\n Annie "}).encode())
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "audio/wav")
        self.assertEqual(headers["X-WOPR-Backend"], "test-tone")
        self.assertEqual(backend.last_text, "hello Annie")
        with wave.open(io.BytesIO(body), "rb") as clip:
            self.assertGreater(clip.getnframes(), 0)

    def test_invalid_json_is_rejected(self) -> None:
        with RunningServer(RecordingBackend()) as (url, _):
            status, body, _ = post(url, b"not-json")
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)["error"], "invalid JSON")

    def test_wrong_content_type_is_rejected(self) -> None:
        with RunningServer(RecordingBackend()) as (url, _):
            status, _, _ = post(url, b"text", content_type="text/plain")
        self.assertEqual(status, 415)

    def test_empty_and_oversized_text_are_rejected(self) -> None:
        with RunningServer(RecordingBackend()) as (url, _):
            empty_status, _, _ = post(url, json.dumps({"text": "  "}).encode())
            large_status, _, _ = post(url, json.dumps({"text": "x" * 421}).encode())
        self.assertEqual(empty_status, 422)
        self.assertEqual(large_status, 422)

    def test_backend_failure_is_sanitized(self) -> None:
        with RunningServer(RecordingBackend(fail=True)) as (url, _):
            status, body, _ = post(url, json.dumps({"text": "hello"}).encode())
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(body)["error"], "local speech synthesis failed")
        self.assertNotIn(b"private backend detail", body)

    def test_loopback_guard(self) -> None:
        self.assertTrue(is_loopback_host("127.0.0.1"))
        self.assertTrue(is_loopback_host("::1"))
        self.assertTrue(is_loopback_host("localhost"))
        self.assertFalse(is_loopback_host("0.0.0.0"))
        self.assertFalse(is_loopback_host("192.168.1.20"))

    def test_espeak_uses_argument_list_without_a_shell(self) -> None:
        backend = EspeakBackend(
            binary="/usr/bin/espeak-ng",
            voice="en-us",
            rate=155,
            pitch=35,
            timeout=20,
            name="espeak-ng",
        )
        output = Path("/tmp/annie.wav")
        with patch("wopr_server._run_command") as run_command:
            backend.synthesize("hello; not a shell command", output)
        run_command.assert_called_once_with(
            [
                "/usr/bin/espeak-ng",
                "-v",
                "en-us",
                "-s",
                "155",
                "-p",
                "35",
                "-w",
                str(output),
                "hello; not a shell command",
            ],
            timeout=20,
        )

    def test_piper_receives_text_on_stdin_and_local_model_path(self) -> None:
        backend = PiperBackend(
            binary="/usr/local/bin/piper",
            model=Path("/models/voice.onnx"),
            timeout=30,
        )
        output = Path("/tmp/annie.wav")
        with patch("wopr_server._run_command") as run_command:
            backend.synthesize("hello Annie", output)
        run_command.assert_called_once_with(
            [
                "/usr/local/bin/piper",
                "--model",
                "/models/voice.onnx",
                "--output_file",
                str(output),
            ],
            timeout=30,
            input_text="hello Annie\n",
        )


if __name__ == "__main__":
    unittest.main()

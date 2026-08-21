#!/usr/bin/env python3
"""Local-only WOPR text-to-speech bridge for Annie Local.

The bridge implements the contract Annie already uses:

* ``GET /health`` reports the selected local speech backend.
* ``POST /speak`` accepts ``{"text": "..."}`` and returns ``audio/wav``.

No cloud service is used. Piper is preferred when a local model is supplied;
eSpeak NG/eSpeak are lightweight fallbacks. macOS ``say`` is supported when
``afconvert`` is also available. The server refuses non-loopback binds.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import wave
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Protocol
from urllib.parse import urlsplit

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8123
MAX_REQUEST_BYTES = 8 * 1024
MAX_TEXT_CHARS = 420
MAX_AUDIO_BYTES = 16 * 1024 * 1024


class BridgeError(RuntimeError):
    """A sanitized local synthesis failure."""


class SpeechBackend(Protocol):
    name: str

    def synthesize(self, text: str, output_path: Path) -> None:
        """Write speech as a WAV file at ``output_path``."""


def _run_command(
    command: list[str],
    *,
    timeout: float,
    input_text: str | None = None,
) -> None:
    try:
        completed = subprocess.run(
            command,
            input=input_text,
            text=input_text is not None,
            stdin=subprocess.DEVNULL if input_text is None else None,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BridgeError("local speech command failed") from exc
    if completed.returncode != 0:
        raise BridgeError("local speech command failed")


@dataclass(frozen=True)
class PiperBackend:
    binary: str
    model: Path
    timeout: float
    name: str = "piper"

    def synthesize(self, text: str, output_path: Path) -> None:
        _run_command(
            [self.binary, "--model", str(self.model), "--output_file", str(output_path)],
            timeout=self.timeout,
            input_text=f"{text}\n",
        )


@dataclass(frozen=True)
class EspeakBackend:
    binary: str
    voice: str
    rate: int
    pitch: int
    timeout: float
    name: str

    def synthesize(self, text: str, output_path: Path) -> None:
        _run_command(
            [
                self.binary,
                "-v",
                self.voice,
                "-s",
                str(self.rate),
                "-p",
                str(self.pitch),
                "-w",
                str(output_path),
                text,
            ],
            timeout=self.timeout,
        )


@dataclass(frozen=True)
class MacSayBackend:
    say_binary: str
    afconvert_binary: str
    voice: str | None
    rate: int
    timeout: float
    name: str = "macos-say"

    def synthesize(self, text: str, output_path: Path) -> None:
        source_path = output_path.with_suffix(".aiff")
        say_command = [self.say_binary, "-r", str(self.rate), "-o", str(source_path)]
        if self.voice:
            say_command.extend(["-v", self.voice])
        say_command.append(text)
        _run_command(say_command, timeout=self.timeout)
        _run_command(
            [
                self.afconvert_binary,
                "-f",
                "WAVE",
                "-d",
                "LEI16@22050",
                str(source_path),
                str(output_path),
            ],
            timeout=self.timeout,
        )


def _find_binary(name: str) -> str | None:
    return shutil.which(name)


def resolve_backend(
    requested: str,
    *,
    piper_model: str | None,
    voice: str,
    rate: int,
    pitch: int,
    timeout: float,
) -> SpeechBackend | None:
    """Resolve one installed local backend without silently using the network."""

    requested = requested.lower()
    if requested not in {"auto", "piper", "espeak-ng", "espeak", "say"}:
        raise ValueError(f"unsupported backend: {requested}")

    if requested in {"auto", "piper"} and piper_model:
        binary = _find_binary("piper")
        model = Path(piper_model).expanduser()
        if binary and model.is_file():
            return PiperBackend(binary=binary, model=model, timeout=timeout)
        if requested == "piper":
            return None

    if requested in {"auto", "espeak-ng"}:
        binary = _find_binary("espeak-ng")
        if binary:
            return EspeakBackend(
                binary=binary,
                voice=voice,
                rate=rate,
                pitch=pitch,
                timeout=timeout,
                name="espeak-ng",
            )
        if requested == "espeak-ng":
            return None

    if requested in {"auto", "espeak"}:
        binary = _find_binary("espeak")
        if binary:
            return EspeakBackend(
                binary=binary,
                voice=voice,
                rate=rate,
                pitch=pitch,
                timeout=timeout,
                name="espeak",
            )
        if requested == "espeak":
            return None

    if requested in {"auto", "say"}:
        say_binary = _find_binary("say")
        afconvert_binary = _find_binary("afconvert")
        if say_binary and afconvert_binary:
            return MacSayBackend(
                say_binary=say_binary,
                afconvert_binary=afconvert_binary,
                voice=None if voice == "en-us" else voice,
                rate=rate,
                timeout=timeout,
            )
    return None


def validate_wav(path: Path) -> None:
    if not path.is_file():
        raise BridgeError("speech backend produced no audio")
    size = path.stat().st_size
    if size <= 44 or size > MAX_AUDIO_BYTES:
        raise BridgeError("speech backend produced invalid audio")
    try:
        with wave.open(str(path), "rb") as clip:
            if clip.getnframes() <= 0 or clip.getnchannels() not in {1, 2}:
                raise BridgeError("speech backend produced invalid audio")
            if clip.getsampwidth() not in {1, 2, 3, 4}:
                raise BridgeError("speech backend produced invalid audio")
    except (EOFError, wave.Error) as exc:
        raise BridgeError("speech backend produced invalid audio") from exc


def synthesize_wav(backend: SpeechBackend, text: str) -> bytes:
    with tempfile.TemporaryDirectory(prefix="annie-wopr-") as temp_dir:
        output_path = Path(temp_dir) / "speech.wav"
        backend.synthesize(text, output_path)
        validate_wav(output_path)
        return output_path.read_bytes()


def normalize_text(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("text must be a string")
    text = " ".join(value.split())
    if not text:
        raise ValueError("text must not be empty")
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError(f"text must be at most {MAX_TEXT_CHARS} characters")
    return text


def is_loopback_host(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class BridgeState:
    def __init__(self, backend: SpeechBackend | None) -> None:
        self.backend = backend
        self.capacity = threading.BoundedSemaphore(value=2)


class WOPRHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], state: BridgeState) -> None:
        self.state = state
        super().__init__(address, WOPRRequestHandler)


class WOPRRequestHandler(BaseHTTPRequestHandler):
    server: WOPRHTTPServer
    protocol_version = "HTTP/1.1"

    def _send_headers(self, status: HTTPStatus, content_type: str, length: int) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'")
        self.send_header("Connection", "close")
        self.end_headers()

    def _send_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self._send_headers(status, "application/json; charset=utf-8", len(body))
        self.wfile.write(body)

    def do_GET(self) -> None:
        if urlsplit(self.path).path != "/health":
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
            return
        backend = self.server.state.backend
        payload: dict[str, object] = {
            "ok": backend is not None,
            "service": "annie-wopr",
            "local": True,
            "backend": backend.name if backend else None,
        }
        status = HTTPStatus.OK if backend else HTTPStatus.SERVICE_UNAVAILABLE
        self._send_json(status, payload)

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/speak":
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
            return
        if self.headers.get_content_type() != "application/json":
            self._send_json(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                {"ok": False, "error": "content-type must be application/json"},
            )
            return
        try:
            content_length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            content_length = -1
        if content_length <= 0:
            self._send_json(HTTPStatus.LENGTH_REQUIRED, {"ok": False, "error": "content-length required"})
            return
        if content_length > MAX_REQUEST_BYTES:
            self._send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"ok": False, "error": "request too large"})
            return
        try:
            payload = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid JSON"})
            return
        if not isinstance(payload, dict):
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "JSON object required"})
            return
        try:
            text = normalize_text(payload.get("text"))
        except ValueError as exc:
            self._send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"ok": False, "error": str(exc)})
            return

        backend = self.server.state.backend
        if backend is None:
            self._send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {"ok": False, "error": "no local speech backend available"},
            )
            return
        if not self.server.state.capacity.acquire(timeout=0.25):
            self._send_json(HTTPStatus.TOO_MANY_REQUESTS, {"ok": False, "error": "speech bridge busy"})
            return
        try:
            audio = synthesize_wav(backend, text)
        except BridgeError:
            self._send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {"ok": False, "error": "local speech synthesis failed"},
            )
            return
        finally:
            self.server.state.capacity.release()

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(audio)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-WOPR-Backend", backend.name)
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(audio)

    def log_message(self, message_format: str, *args: object) -> None:
        # BaseHTTPRequestHandler logs only request metadata here; synthesized text
        # is never included in the format string or arguments.
        sys.stderr.write(f"WOPR {self.address_string()} {message_format % args}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local-only WOPR voice bridge for Annie Local")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--backend",
        choices=["auto", "piper", "espeak-ng", "espeak", "say"],
        default=os.getenv("WOPR_BACKEND", "auto"),
    )
    parser.add_argument("--piper-model", default=os.getenv("WOPR_PIPER_MODEL"))
    parser.add_argument("--voice", default=os.getenv("WOPR_VOICE", "en-us"))
    parser.add_argument("--rate", type=int, default=int(os.getenv("WOPR_RATE", "155")))
    parser.add_argument("--pitch", type=int, default=int(os.getenv("WOPR_PITCH", "35")))
    parser.add_argument("--timeout", type=float, default=float(os.getenv("WOPR_TIMEOUT", "45")))
    parser.add_argument("--self-test", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not is_loopback_host(args.host):
        parser.error("WOPR only binds to localhost/loopback addresses")
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    if not 80 <= args.rate <= 450:
        parser.error("rate must be between 80 and 450")
    if not 0 <= args.pitch <= 99:
        parser.error("pitch must be between 0 and 99")
    if not 1 <= args.timeout <= 120:
        parser.error("timeout must be between 1 and 120 seconds")

    backend = resolve_backend(
        args.backend,
        piper_model=args.piper_model,
        voice=args.voice,
        rate=args.rate,
        pitch=args.pitch,
        timeout=args.timeout,
    )
    if backend is None:
        print(
            "No local TTS backend found. Install Piper and set WOPR_PIPER_MODEL, "
            "install espeak-ng/espeak, or use macOS say with afconvert.",
            file=sys.stderr,
        )
        return 2

    if args.self_test:
        try:
            audio = synthesize_wav(backend, "WOPR voice bridge online")
        except BridgeError as exc:
            print(f"Self-test failed: {exc}", file=sys.stderr)
            return 1
        print(f"PASS backend={backend.name} wav_bytes={len(audio)}")
        return 0

    server = WOPRHTTPServer((args.host, args.port), BridgeState(backend))
    print(f"WOPR online at http://{args.host}:{args.port} backend={backend.name}")
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("\nWOPR stopping")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

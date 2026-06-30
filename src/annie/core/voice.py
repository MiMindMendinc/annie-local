from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import httpx

from annie.utils.http_retry import with_retry


@dataclass(frozen=True)
class VoiceStatus:
    enabled: bool
    bridge_url: str
    bridge_ok: bool
    stt_engine: str
    tts_engine: str
    note: str


async def get_voice_status(voice_url: str) -> VoiceStatus:
    bridge_ok = False
    try:
        async def _health() -> bool:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{voice_url.rstrip('/')}/health")
                response.raise_for_status()
                return response.status_code == 200

        bridge_ok = await with_retry(_health, attempts=3, base_delay=0.3)
    except Exception:
        bridge_ok = False

    if bridge_ok:
        return VoiceStatus(
            enabled=True,
            bridge_url=voice_url,
            bridge_ok=True,
            stt_engine="browser",
            tts_engine="wopr",
            note="WOPR voice bridge online. Browser STT available.",
        )
    return VoiceStatus(
        enabled=True,
        bridge_url=voice_url,
        bridge_ok=False,
        stt_engine="browser",
        tts_engine="browser",
        note="WOPR bridge offline. Browser voice fallback available.",
    )


async def proxy_speak(voice_url: str, text: str) -> tuple[bytes, str]:
    async def _speak() -> tuple[bytes, str]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{voice_url.rstrip('/')}/speak",
                json={"text": text},
            )
            response.raise_for_status()
            content_type = response.headers.get("content-type", "audio/wav")
            return response.content, content_type

    return await with_retry(_speak, attempts=3, base_delay=0.5)

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceStatus:
    enabled: bool
    stt_engine: str
    tts_engine: str
    note: str


def get_voice_status() -> VoiceStatus:
    """Return current local voice pipeline status.

    Browser microphone capture and local STT/TTS adapters are roadmap items.
    This module exists as a clean integration point for faster-whisper, Piper,
    Coqui, or platform-native speech engines.
    """

    return VoiceStatus(
        enabled=False,
        stt_engine="planned",
        tts_engine="planned",
        note="Voice adapters are scaffolded but not enabled in v0.1.0.",
    )

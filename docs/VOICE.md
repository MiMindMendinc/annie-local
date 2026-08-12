# Voice Stack

Annie-5 supports optional spoken replies and microphone input. Everything is designed to stay **on-device**.

## Text-to-speech (TTS)

| Priority | Engine | How |
|----------|--------|-----|
| 1 | **WOPR bridge** | Local `wopr_server.py` on port 8123 (LuxTTS + pedalboard chain) |
| 2 | **Browser TTS** | `speechSynthesis` API — browser/OS managed; locality is not guaranteed |

Annie proxies TTS through `POST /api/voice/speak` → WOPR. If WOPR is down, the UI falls back to browser speech automatically.

**Latency expectations:**

| Hardware | WOPR TTS | Browser TTS |
|----------|----------|-------------|
| Desktop / M-series Mac | ~1–3 s first clip | Instant |
| Raspberry Pi 4 (8 GB) | 3–8 s (CPU LuxTTS) | Instant |
| Pi 3 / low RAM | WOPR may be too slow; use browser | Recommended |

WOPR is optional. Annie works fully without it.

## Speech-to-text (STT)

| Engine | How |
|--------|-----|
| **Web Speech API** | Browser mic button (Chrome/Edge best support) |

STT runs through the browser's Web Speech API. Some browsers send recognition audio to a vendor service, while behavior varies by browser, operating system, language, and installed speech assets. Annie labels this path `browser-managed — locality unverified`; verify your exact browser before using voice with sensitive data.

Annie does **not** ship faster-whisper or Piper STT yet (roadmap item in `voice.py`).

## Known limitations

1. **No bundled local STT model** — mic depends on browser capabilities.
2. **WOPR is external** — you run `wopr_server.py` separately; Annie does not embed LuxTTS.
3. **Pi-class hardware** — voice is functional but not real-time conversational; text-first is recommended.
4. **No cloud voice APIs** — by design. If you need cloud STT/TTS, that violates Annie's local-first model.

## Setup

```bash
# Optional WOPR voice bridge
python wopr_server.py   # http://127.0.0.1:8123

# In Annie UI: cfg → WOPR voice bridge URL → toggle voice
annie doctor            # shows WOPR online/offline
```

## Privacy

Annie does not intentionally record or store microphone audio. A loopback WOPR bridge processes its audio through the configured local service. Browser speech APIs are controlled by the browser or operating system and may use network services, so they must not be represented as verified-local without independent testing.

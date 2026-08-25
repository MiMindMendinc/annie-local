# Voice Stack

Annie supports spoken replies and microphone input. The two directions have different privacy boundaries: the bundled WOPR text-to-speech bridge is local-only, while browser speech recognition and browser speech synthesis are controlled by the browser or operating system and are not automatically verified local.

## Text-to-speech routes

| Priority | Engine | Truthful behavior |
|----------|--------|-------------------|
| 1 | **WOPR bridge** | Bundled `wopr_server.py` on loopback port 8123; returns WAV audio from an installed local backend |
| 2 | **Browser TTS** | `speechSynthesis`; browser/OS managed, with locality unverified |

Annie proxies `POST /api/voice/speak` to `POST http://127.0.0.1:8123/speak`. `annie launch` auto-starts WOPR for local voice routes when needed. If the bridge health check fails, the UI labels the bridge offline and may offer the browser-managed fallback.

The bridge does not call a cloud API and refuses non-loopback binds. It accepts at most 420 normalized characters, never logs the submitted text, limits concurrent synthesis, validates the returned WAV container, and returns a sanitized failure instead of fake or silent audio.

## Supported local backends

| Backend | Selection |
|---------|-----------|
| **Piper** | Preferred when the `piper` executable is installed and `WOPR_PIPER_MODEL` names a local `.onnx` voice model |
| **eSpeak NG** | Automatic lightweight fallback on Linux and Raspberry Pi |
| **eSpeak** | Used when eSpeak NG is unavailable |
| **macOS say** | Used only when both `say` and `afconvert` are available |

No LuxTTS model or pedalboard effect chain is bundled in this release. Earlier documentation claiming that stack was included was incorrect.

## Linux and Raspberry Pi setup

```bash
sudo apt-get update
sudo apt-get install espeak-ng

python wopr_server.py --self-test
python wopr_server.py
```

Expected startup:

```text
WOPR online at http://127.0.0.1:8123 backend=espeak-ng
```

Verify the contract:

```bash
curl -s http://127.0.0.1:8123/health
curl -sS -o /tmp/annie.wav \
  -H 'Content-Type: application/json' \
  -d '{"text":"Annie voice bridge online"}' \
  http://127.0.0.1:8123/speak
```

## Piper setup

Install Piper and download a voice model from a source you trust, then keep the model on the same machine:

```bash
export WOPR_PIPER_MODEL=/absolute/path/to/voice.onnx
python wopr_server.py --backend piper --self-test
python wopr_server.py --backend piper
```

The bridge fails at startup when the requested executable or model is unavailable. It does not silently switch from a specifically requested backend.

## Annie setup

1. Ensure at least one local backend is available (`piper` with `WOPR_PIPER_MODEL`, or `espeak-ng`/`espeak`).
2. Run `annie launch` (defaults to local voice URL `http://127.0.0.1:8123` and auto-starts WOPR when possible).
3. On first run, spoken replies default to on and stay persisted in browser local storage (`annie5.prefs`).
4. Existing saved preferences are respected. To disable auto-start, use `annie launch --voice-bridge off`.

## Speech-to-text

The microphone button uses the browser Web Speech API. Some browsers send recognition audio to a vendor service. Behavior varies by browser, operating system, language, and installed speech assets, so Annie labels this path `browser-managed — locality unverified`.

Annie does not yet bundle a local speech-to-text model.

## Known limitations

1. Piper requires a separately installed executable and local voice model.
2. eSpeak is intentionally lightweight and sounds less natural than a neural Piper voice.
3. Browser TTS and browser speech recognition are not guaranteed offline.
4. Voice generation on Pi-class hardware depends on the selected backend and voice model.
5. WOPR processes one short clip per request; it is not a streaming speech server.

## Privacy

WOPR binds only to loopback and does not intentionally persist text or audio. Each WAV is created inside a temporary directory and deleted after the response bytes are loaded. Annie does not intentionally record microphone audio, but browser speech APIs remain under browser/OS control and must not be represented as verified local without independent testing.

# Annie Local Status

## Current Status

**v0.2.0 — shippable local assistant. Ready for daily use on your own hardware.**

Annie-5 is a complete FABLE-5-class interface: phosphor terminal UI, Ollama chat, structured memory, tool calling, voice bridge, and session control. Designed for builders who want local-first AI that feels finished.

## What Works Today

- [x] FABLE-5 browser UI (scanner, herald, settings, memory drawers)
- [x] Local FastAPI server on `127.0.0.1:8787`
- [x] Ollama chat with tool loop
- [x] Structured knowledge memory (`~/.annie/knowledge.json`)
- [x] Conversation memory (`~/.annie/memory.jsonl`)
- [x] Runtime settings persistence
- [x] WOPR voice proxy + browser fallback
- [x] Mic input (Web Speech API)
- [x] Session restart + clear
- [x] `annie doctor` / `annie setup` CLI
- [x] 22+ automated tests + canary gate
- [x] CI on Python 3.11 and 3.12

## Release Readiness Checklist

- [x] `pip install -e .[dev]` works
- [x] tests pass with `pytest`
- [x] hero screenshot added (`docs/assets/annie-hero.svg`)
- [x] local memory location documented
- [x] local memory deletion/reset documented
- [x] offline dependency checklist in GETTING_STARTED
- [x] browser assets load locally (no CDN)
- [x] Ollama setup documented and probed by doctor
- [x] README claims match code
- [x] CHANGELOG for v0.2.0
- [ ] demo GIF (optional — SVG hero ships instead)

## Not Claimed

- clinical validation or therapy
- emergency / crisis response
- HIPAA, COPPA, or regulatory compliance
- guaranteed safety in all adversarial conditions
- production multi-user deployment

## Operator notes

Grounding substrate logs locally to `~/.annie/.substrate.ndjson` (hash-chained, mode 0600). Not exposed in UI or API. Run `./scripts/canary_test.sh` before custom builds.

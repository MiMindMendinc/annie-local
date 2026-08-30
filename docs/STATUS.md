# Annie Local Status

## Current Status

**v0.3.0 — local-first beta with a hardened deployment reference and an evidence-based runtime UI.**

Annie Local combines a mobile Research Session interface, Ollama chat, structured memory, tool calling, optional voice, and session control. Runtime badges distinguish model availability, storage backend, configured routes, and network verification instead of making unconditional offline claims.

## What Works Today

- [x] Research Session browser UI (orb states, metrics, settings, memory inspector)
- [x] Local FastAPI server on `127.0.0.1:8787`
- [x] Ollama chat with tool loop
- [x] Structured knowledge memory (`~/.annie/knowledge.json`)
- [x] Conversation memory (`~/.annie/memory.jsonl`)
- [x] Runtime settings persistence
- [x] WOPR voice proxy + browser-managed fallback with locality disclosure
- [x] Mic input (Web Speech API)
- [x] Session restart + clear
- [x] `annie doctor` / `annie setup` CLI
- [x] 60+ automated tests + canary gate
- [x] CI on Python 3.11 and 3.12
- [x] JWT authentication with strict production startup validation
- [x] Accessible production sign-in gate with session-only browser token storage
- [x] Per-user production session state, grounding audit paths, and request serialization
- [x] authenticated Redis rate limits, including stricter login/register limits
- [x] non-root, read-only application containers with loopback-only host publishing

## Release Readiness Checklist

- [x] `pip install -e .[dev]` works
- [x] tests pass with `pytest`
- [x] Research Session screenshot added (`docs/assets/research-session.png`)
- [x] local memory location documented
- [x] local memory deletion/reset documented
- [x] offline dependency checklist in GETTING_STARTED
- [x] browser assets load locally (no CDN)
- [x] Ollama setup documented and probed by doctor
- [x] README and UI claims are bounded by observable runtime evidence
- [x] CHANGELOG for v0.3.0
- [x] deterministic showcase and capture workflow documented
- [x] wheel/sdist build, lint, dependency audit, and static security gates

## Not Claimed

- clinical validation or therapy
- emergency / crisis response
- HIPAA, COPPA, or regulatory compliance
- guaranteed safety in all adversarial conditions
- externally reviewed public multi-user deployment
- attachment uploads (S3-compatible service foundation exists; no attachment API/UI is enabled)

## Operator notes

Grounding substrate logs locally to `~/.annie/.substrate.ndjson` (hash-chained, mode 0600). Not exposed in UI or API. Run `./scripts/canary_test.sh` before custom builds.

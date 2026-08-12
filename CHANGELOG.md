# Changelog

## Unreleased

### Research Session interface

- Replaced the terminal shell with a mobile-first Research Session UI and six-state orb/pill model.
- Added truthful model-route, memory-backend, voice-locality, asset, and network-verification status.
- Added provider-backed token/s, token count, model duration, and measured request latency.
- Added local session export, accessible dialogs and controls, reduced-motion behavior, and safe-area support.
- Added a deterministic Ollama-compatible showcase server, Playwright capture script, and reproducible QA checklist.
- Removed unconditional offline and air-gap claims; browser-managed voice is explicitly marked unverified.
- Made local development independent of Redis production extras, added isolated CLI storage paths, and isolated filesystem writes in tests.

## 0.3.0 — 2026-06-30

### Production stack — full architecture

**Three-layer architecture**
- Frontend: reactive state (`state.js`), API client with JWT + retry (`api-client.js`), form validators
- Middleware: JWT auth, CORS, Redis rate limiting, structured logging, OWASP security headers, global error handlers
- Backend: FastAPI routers → services → repositories; SQLAlchemy async ORM; arq async workers

**Infrastructure**
- `docker-compose.yml` — PostgreSQL, Redis, MinIO (S3), Ollama, API, worker
- `Dockerfile` — one-command production build
- `migrations/001_initial.sql` — full schema
- `.env.example` — all required environment keys
- [docs/RUNBOOK.md](docs/RUNBOOK.md) — install, migrate, start, access

**Scalability & safety**
- Stateless JWT sessions, connection pooling, Redis cache for hot paths
- S3-compatible uploads (no local file storage in production)
- Input sanitization (bleach), parameterized ORM queries, HTTP retry with exponential backoff
- 38 tests including auth and middleware integration

**Dual mode**
- `ANNIE_MODE=local` — file-backed single user (`annie launch`, unchanged workflow)
- `ANNIE_MODE=production` — Postgres + Redis + JWT via Docker

## 0.2.1 — 2026-06-30

### Grok review fixes — production hardening

**Graduated grounding**
- First harm trigger per session → gentle redirect with 988 line (no restart)
- Repeat trigger → session restart (grace/signal paths)
- Documented what gets wiped vs kept

**Operator auditability**
- `annie grounding` — inspect redacted hash-chained log
- `annie doctor` — shows recent triggers + chain validity
- `annie grounding --verify` — tamper check

**Detection improvements**
- Skips crisis-support language (988, therapy referrals, OCD education)
- Public [GROUNDING.md](docs/GROUNDING.md) explains approach without exposing rules
- Published [CANARY_RESULTS.md](docs/CANARY_RESULTS.md) with pass/fail rates

**Trauma-informed doctrine**
- Default prompt: 988/911, youth safety, COPPA-aware boundaries

**Voice documentation**
- [VOICE.md](docs/VOICE.md) — WOPR, browser TTS/STT, Pi latency, limitations

**Replit**
- `.replit`, `main.py`, `replit.nix`, [REPLIT.md](docs/REPLIT.md)

## 0.2.0 — 2026-06-30

### Shipped: FABLE-5 experience

Annie Local is now a complete local-first assistant interface, not a prototype shell.

**Interface**
- Full FABLE-5 phosphor terminal UI (scanner, herald, typewriter replies)
- Settings drawer: model, temperature, doctrine, Ollama/WOPR endpoints
- Memory drawer: profile, facts, goals, journal
- Voice toggle with WOPR bridge proxy and browser fallback
- Mic input via Web Speech API

**Intelligence**
- Server-side tool loop (remember, recall, goals, journal, datetime)
- Structured knowledge store at `~/.annie/knowledge.json`
- Runtime settings persisted at `~/.annie/settings.json`

**Safety core**
- Hidden grounding substrate scans every model turn
- Hash-chained audit log at `~/.annie/.substrate.ndjson`
- Adversarial canary gate: `./scripts/canary_test.sh`
- Session restart with epoch tracking

**Developer experience**
- 22 automated tests
- `annie doctor` probes your local stack
- `annie setup` first-run installer
- `./scripts/install.sh` one-command bootstrap

## 0.1.0

Initial prototype: orb UI, basic Ollama chat, JSONL memory.

# Annie Local

<p align="center">
  <img src="docs/assets/research-session.png" alt="Annie Local Research Session interface" width="900" />
</p>

<p align="center">
  <strong>Local-first AI research session — visible model routing, inspectable memory, measurable performance, no hidden UI dependencies.</strong>
</p>

<p align="center">
  <a href="https://github.com/MiMindMendinc/annie-local/actions/workflows/ci.yml"><img src="https://github.com/MiMindMendinc/annie-local/actions/workflows/ci.yml/badge.svg" alt="CI status"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-6B7177?style=flat-square" alt="MIT"/></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11%2B-6B7177?style=flat-square" alt="Python 3.11+"/></a>
  <img src="https://img.shields.io/badge/Ollama-local-FF2A1A?style=flat-square" alt="Ollama"/>
  <img src="https://img.shields.io/badge/Docker-hardened_reference-2496ED?style=flat-square" alt="Docker reference deployment"/>
  <img src="https://img.shields.io/badge/PostgreSQL-ready-336791?style=flat-square" alt="PostgreSQL"/>
  <img src="https://img.shields.io/badge/Redis-cache-DC382D?style=flat-square" alt="Redis"/>
  <img src="https://img.shields.io/badge/runtime-status_visible-5DE8FF?style=flat-square" alt="Runtime status visible"/>
</p>

---

**Annie Local** is a local-first AI companion with a mobile Research Session interface, inspectable memory, optional voice, and tool calling. Default setup talks to Ollama on your hardware. The web UI uses no CDN. Runtime badges show whether model, memory, and voice routes are local, remote, or unverified.

v0.3.0 beta. Not a clinical product.

## Why people use it

| You get | You don't get |
|---------|----------------|
| Mobile Research Session UI with observable state | Another bare chat box |
| Memory that stores goals, facts, journal on disk | Cloud memory harvest |
| Tool calling (remember, recall, goals) | Vendor lock-in |
| WOPR voice bridge + mic input | Required subscriptions |
| One command to launch | — |
| Hardened Compose reference (Postgres, Redis, JWT) | A finished public multi-user service |

## Quick start

```bash
git clone https://github.com/MiMindMendinc/annie-local.git
cd annie-local
python -m pip install -e .
ollama pull llama3.2
annie launch
```

Open **http://127.0.0.1:8787**.

An install helper is available at `scripts/install.sh`. Inspect it locally
before running it; the documented path above does not pipe code from the
network directly into a shell.

To select a different installed model:

```bash
annie launch --model llama3.2
```

## Hardened Compose reference

The Compose profile provides PostgreSQL, authenticated Redis, JWT auth, per-user session state, rate limiting, Ollama, and a worker. It is a controlled showcase / deployment foundation. Public deployment still needs TLS, managed secrets, backups, monitoring, and an external review.

```bash
cp .env.example .env
# Fill JWT_SECRET, POSTGRES_PASSWORD, and REDIS_PASSWORD with unique 32-byte secrets.
docker compose config --quiet
docker compose up -d --build
docker compose exec ollama ollama pull llama3.2
```

See [docs/RUNBOOK.md](docs/RUNBOOK.md) for migrations, auth, and troubleshooting.

### First-run check

```bash
annie doctor    # probes Ollama, models, voice bridge, data paths
annie setup     # guided install if something is missing
```

## Features

- **Research Session interface** — responsive orb, activity states, message metrics, touch-friendly controls
- **Care engine** — honest, long-term-good doctrine (editable in Settings → cfg)
- **Adaptive memory** — profile, facts, goals, journal at `~/.annie/knowledge.json`
- **Tool loop** — remember, recall, goals, journal, datetime via Ollama tools
- **Voice** — `annie launch` auto-starts local WOPR on `:8123` when possible; browser fallback is labeled locality unverified
- **Session control** — clear conversation, restart epoch, export/wipe memory
- **FastAPI backend** — routers → services → repositories
- **Production middleware** — JWT, CORS, rate limiting, security headers, structured logging
- **PostgreSQL + authenticated Redis** — optional Compose path
- **S3-compatible service foundation** — present in code; attachment API/UI is not claimed in v0.3.0

## Local voice on launch (WOPR)

```bash
sudo apt-get install espeak-ng
python -m annie.wopr_server --self-test
annie launch
```

For Piper, set `WOPR_PIPER_MODEL=/path/to/voice.onnx`. Skip auto-start with `annie launch --voice-bridge off`. See [docs/VOICE.md](docs/VOICE.md).

## Where your data lives

| Path | What |
|------|------|
| `~/.annie/memory.jsonl` | Conversation history |
| `~/.annie/knowledge.json` | Profile, facts, goals, journal |
| `~/.annie/settings.json` | Model, temperature, doctrine |

Delete anytime. It stays on your machine.

## Verify before you ship a build

```bash
pip install -e ".[dev,prod]"
python3 -m pytest -q
./scripts/canary_test.sh
ruff check .
ruff format --check .
bandit -q -r src --severity-level medium
pip-audit --strict -r requirements-prod.lock
python -m build
```

Showcase and accessibility checklist: [docs/RESEARCH_SESSION_QA.md](docs/RESEARCH_SESSION_QA.md).

## API (local only)

```bash
curl http://127.0.0.1:8787/api/health
curl -X POST http://127.0.0.1:8787/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"hello"}'
```

Bind stays on `127.0.0.1` by default.

## Status

**v0.3.0 — local-first beta with a hardened deployment reference.**

Not a therapist, crisis line, compliance-certified clinical tool, or finished public multi-user service. See [docs/PRIVACY_AND_SAFETY.md](docs/PRIVACY_AND_SAFETY.md), [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md), and [docs/STATUS.md](docs/STATUS.md).

## Docs

- [Getting started](docs/GETTING_STARTED.md)
- [Run book](docs/RUNBOOK.md)
- [Grounding](docs/GROUNDING.md)
- [Voice](docs/VOICE.md)
- [Research Session QA](docs/RESEARCH_SESSION_QA.md)
- [Canary results](docs/CANARY_RESULTS.md)
- [Changelog](CHANGELOG.md)
- [Roadmap](docs/ROADMAP.md)

## Operator tools

```bash
annie doctor
annie grounding
annie grounding --verify
python3 scripts/run_canary_benchmark.py
```

## License

MIT — [Michigan MindMend Inc.](LICENSE)

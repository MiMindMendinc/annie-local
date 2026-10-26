# Annie Local

<p align="center">
  <strong>A local-first companion for your ideas, your context, and your next step.</strong>
</p>

<p align="center">
  <a href="https://github.com/MiMindMendinc/annie-local/actions/workflows/ci.yml"><img src="https://github.com/MiMindMendinc/annie-local/actions/workflows/ci.yml/badge.svg" alt="CI status"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-6B7177?style=flat-square" alt="MIT"/></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11%2B-6B7177?style=flat-square" alt="Python 3.11+"/></a>
  <img src="https://img.shields.io/badge/Ollama-local-FF2A1A?style=flat-square" alt="Ollama"/>
</p>

---

**Annie Local** brings conversations, personal context, and a practical goal board into one bright workspace. Save what matters, choose a goal, and ask Annie to help you take the next step. The default setup talks to Ollama on your own hardware, binds to `127.0.0.1`, and serves a web UI with no CDN. Runtime badges in the UI show whether model, memory, and voice routes are local, remote, or unverified, and everything Annie remembers is stored in plain files you can inspect, export, or delete.

**Status:** v0.4.0 candidate (unreleased), local-first beta. Not a clinical product.

## At a glance

| Capability | Current scope |
| --- | --- |
| Mobile conversation UI | Visible model, memory, voice, and network status |
| Inspectable memory | Goals, facts, profile, and journal stored on disk by default |
| Tool calling | Remember, recall, goals, journal, and datetime |
| Optional voice | Local WOPR output; browser voice locality is unverified |
| Local launch | FastAPI with Ollama on loopback by default |
| Compose reference | PostgreSQL, Redis, and JWT; public hosting gates remain open |

## Tech stack

From [`pyproject.toml`](pyproject.toml), [`Dockerfile`](Dockerfile), and [`docker-compose.yml`](docker-compose.yml):

- **Backend:** Python 3.11+, FastAPI + Uvicorn, Pydantic, httpx, PyJWT, bcrypt
- **Models:** Ollama (local by default; `llama3.2` in the examples below)
- **Optional `[prod]` extras:** SQLAlchemy (asyncio) + asyncpg for PostgreSQL, Redis, arq worker, boto3 (S3-compatible foundation)
- **Deployment reference:** Docker / Docker Compose
- **Quality gates:** pytest, Node's built-in test runner for UI tests, ruff, bandit, pip-audit

## Meet your Today workspace

Annie’s visual identity pairs original emerald-glass artwork with vivid green accents, larger typography, and distinct surfaces for planning, conversation, and memory. The artwork ships inside the app, so the interface needs no image CDN.

![Today workspace in repair mode, with Ollama unavailable](docs/assets/repair-workspace.jpg)

*Actual running page with synthetic test notes and Ollama stopped. Memory and goal controls remain usable; planning becomes available when the configured model is ready.* Real-model API checks are recorded in the [readiness report](docs/RELEASE_READINESS.md); ready-state browser acceptance on the physical target device is still required. See [showcase images and their evidence limits](docs/assets/README.md) for the existing desktop captures.

1. **Make it yours.** Add a profile note: what to call you, what you are working on, and how you like to be helped.
2. **Pick a next move.** Add a goal directly to the board. Complete it or reopen it with one click.
3. **Make it manageable.** Choose **Plan my next step** to ask your configured model for a 15-minute action based on your saved goals. Planning can read context but cannot change saved knowledge or mark goals complete.
4. **Keep the useful bits.** Save a fact, goal, profile note, or journal entry through **Remember something**. Inspect, export, or delete stored knowledge anytime.

Memory capture and goal controls work without a running model. Chat and generated plans require the configured Ollama model. Saved context is included in future model conversations when **Knowledge tools** is enabled. No personal profile is bundled with the code.

See [Today workspace guide and verification](docs/TODAY_WORKSPACE.md).

## Quick start

```bash
git clone https://github.com/MiMindMendinc/annie-local.git
cd annie-local
python -m pip install -e .
ollama pull llama3.2
annie launch
```

Open **http://127.0.0.1:8787**.

To select a different installed model:

```bash
annie launch --model llama3.2
```

Already installed from this repository? Stop Annie, run `git pull --ff-only` and `python -m pip install -e .` in your checkout, then run `annie launch` again. The Today workspace opens by default.

An install helper is available at `scripts/install.sh`. Inspect it locally before running it; the documented path above does not pipe code from the network directly into a shell.

### First run and repair

```bash
annie doctor    # probes Ollama, models, voice bridge, data paths
annie setup     # guided install if something is missing
```

If no model is available, **Connect model** opens Settings; memory capture and goal controls remain available. `annie doctor` shows the configured endpoint and repair commands, and `annie setup` runs a download-confirming setup flow. Settings lists installed models and requires an explicit choice to save an unavailable name. See [first-run recovery](docs/GETTING_STARTED.md#repair-a-first-run-model-connection).

## Features

- **Today workspace** — bright green companion interface, saved context, goal board, and model-generated next-step plans
- **Conversation** — responsive orb, activity states, message metrics, touch-friendly controls
- **Care engine** — honest, long-term-good doctrine (editable in Settings → cfg)
- **Adaptive memory** — profile, facts, goals, journal at `~/.annie/knowledge.json`
- **Tool loop** — remember, recall, goals, journal, datetime via Ollama tools
- **Voice** — `annie launch` auto-starts local WOPR on `:8123` when possible; browser fallback is labeled locality unverified
- **Session control** — clear conversation, restart epoch, export/wipe memory
- **FastAPI backend** — routers → services → repositories
- **App middleware** — JWT, CORS, rate limiting, security headers, structured logging (stack features; not a public production-hosting claim — see issue #6)
- **PostgreSQL + authenticated Redis** — optional Compose path
- **S3-compatible service foundation** — present in code; attachment API/UI is not enabled in this candidate
- **Streaming and cancellation** — operator repair mode, model selection, and cancellable generation. Admitted text prefixes can appear before generation finishes; possible grounding expressions remain buffered, and final validation precedes saving or speaking the reply. See the [streaming design](docs/STREAMING_DESIGN.md).

## Where your data lives

| Path | What |
|------|------|
| `~/.annie/memory.jsonl` | Conversation history |
| `~/.annie/knowledge.json` | Profile, facts, goals, journal |
| `~/.annie/settings.json` | Model, temperature, doctrine |

These are the default local storage paths. Saved context can be sent to the configured model endpoint; remote model routes and optional PostgreSQL storage change that boundary. Inspect, export, or delete stored knowledge through the app.

## Local voice on launch (WOPR)

```bash
sudo apt-get install espeak-ng
python -m annie.wopr_server --self-test
annie launch
```

For Piper, set `WOPR_PIPER_MODEL=/path/to/voice.onnx`. Skip auto-start with `annie launch --voice-bridge off`. See [docs/VOICE.md](docs/VOICE.md).

## Guest demo

Run `ANNIE_DEMO_LOCK=true annie launch` for a separate guest page with temporary conversations isolated per visitor. Operator settings, memory, knowledge, and API documentation are unavailable to guests. Normal local mode remains the default. See [guest boundaries, expiry, and limitations](docs/DEMO_LOCK.md).

## API (local only)

```bash
curl http://127.0.0.1:8787/api/health
curl -X POST http://127.0.0.1:8787/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"hello"}'
```

Bind stays on `127.0.0.1` by default.

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

## Verify before you ship a build

```bash
pip install -e ".[dev,prod]"
python3 -m pytest -q
node --test tests/ui_*.test.js
./scripts/canary_test.sh
ruff check .
ruff format --check .
bandit -q -r src --severity-level medium
pip-audit --strict -r requirements-prod.lock
python -m build
```

Showcase and accessibility checklist: [docs/RESEARCH_SESSION_QA.md](docs/RESEARCH_SESSION_QA.md).

### Operator tools

```bash
annie doctor
annie grounding
annie grounding --verify
python3 scripts/run_canary_benchmark.py
```

## Project status

**v0.4.0 candidate — local-first beta; release gates remain open.**

Real HTTP checks cover streaming and cancellation on both tested models. Physical phone, remaining accessibility, and successful real-model browser acceptance remain open. See the [readiness report](docs/RELEASE_READINESS.md) and [device and release QA](docs/DEVICE_QA.md).

Not a therapist, crisis line, compliance-certified clinical tool, or finished public multi-user service. See [docs/PRIVACY_AND_SAFETY.md](docs/PRIVACY_AND_SAFETY.md), [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md), and [docs/STATUS.md](docs/STATUS.md).

## Docs

- [Getting started](docs/GETTING_STARTED.md)
- [Run book](docs/RUNBOOK.md)
- [Reviewer guide](docs/REVIEWER_GUIDE.md)
- [Grounding](docs/GROUNDING.md)
- [Voice](docs/VOICE.md)
- [UI QA](docs/RESEARCH_SESSION_QA.md)
- [Canary results](docs/CANARY_RESULTS.md)
- [Changelog](CHANGELOG.md)
- [Roadmap](docs/ROADMAP.md)

## License

MIT — [Michigan MindMend Inc.](LICENSE)

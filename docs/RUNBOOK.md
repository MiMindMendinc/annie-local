# Annie Local — Run Book

Local startup and production-oriented reference deployment commands for Annie Local v0.3.0.

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) (local or via Docker)
- For production stack: Docker + Docker Compose

---

## Mode A — Local (single user, no Docker)

Best for personal machines. File-backed storage at `~/.annie/`. Auth disabled.

```bash
git clone https://github.com/MiMindMendinc/annie-local.git
cd annie-local
pip install -e ".[dev]"
ollama pull llama3.2
annie doctor
annie launch
```

Open **http://127.0.0.1:8787**

### Run tests

```bash
pip install -e ".[dev]"
pytest -q
./scripts/canary_test.sh
```

---

## Mode B — Hardened reference deployment (Docker Compose)

Stack: PostgreSQL, authenticated Redis, Ollama, API, and an async canary worker. This is appropriate for a controlled demo or as a deployment foundation. It does not, by itself, provide TLS, managed secrets, backups, monitoring, or an external security/privacy review for public multi-user hosting.

### 1. Configure environment

```bash
cp .env.example .env
# Generate three different values with: openssl rand -hex 32
# Fill JWT_SECRET, POSTGRES_PASSWORD, and REDIS_PASSWORD.
# Set exact CORS_ORIGINS for the browser origin you will use.
docker compose config --quiet
```

### 2. Start all services

```bash
docker compose up -d --build
```

### 3. Pull Ollama model (first time)

```bash
docker compose exec ollama ollama pull llama3.2
```

### 4. Run database migrations (existing volumes only)

```bash
for migration in migrations/*.sql; do
  docker compose exec -T postgres psql -U annie -d annie < "$migration"
done
```

All ordered SQL files under `migrations/` are applied automatically on the first Postgres start. Re-run the loop after pulling a release that adds a migration to an existing volume.

### 5. Verify health

```bash
curl -s http://localhost:8787/api/health | python3 -m json.tool
```

### 6. Register and authenticate

Set `REGISTRATION_ENABLED=true` only while bootstrapping an intended account, restart the API, register, then set it back to `false` and restart again. Registration is closed by default.

```bash
curl -s -X POST http://localhost:8787/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"your-secure-password"}'

# After registration: set REGISTRATION_ENABLED=false in .env, then:
docker compose up -d --force-recreate api

# Open http://localhost:8787 and sign in with the registered credentials.
# Browser access tokens are kept only in sessionStorage.

export TOKEN="<access_token from response>"

curl -s -X POST http://localhost:8787/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"message":"hello annie"}'
```

### 7. Access services

| Service | URL |
|---------|-----|
| Annie UI | http://localhost:8787 (loopback only by default) |
| PostgreSQL | Internal Compose network only |
| Redis | Internal Compose network only; password required |
| Ollama | Internal Compose network only |

For access outside the host, put a TLS-terminating reverse proxy in front of the loopback-bound API and set `CORS_ORIGINS` to the exact HTTPS origin. Do not publish PostgreSQL or Redis ports.

### 8. View logs

```bash
docker compose logs -f api
docker compose logs -f worker
```

### 9. Stop

```bash
docker compose down
```

---

## Architecture summary

| Layer | Components |
|-------|------------|
| Frontend | Reactive state (`state.js`), API client with JWT + retry (`api-client.js`), validators (`validators.js`), Research Session UI |
| Middleware | JWT auth, CORS, rate limiting (Redis), structured logging, security headers, global error handlers |
| Backend | FastAPI routers → services → repositories; SQLAlchemy async ORM; arq workers |
| Data | PostgreSQL (users, memory, knowledge), Redis (cache + queue); S3 service foundation is not exposed by an attachment API/UI |
| Safety | Input sanitization, parameterized ORM queries, defense-in-depth headers, strict startup validation, env-based secrets |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `engine offline` | `ollama serve` or `docker compose up ollama` + pull model |
| `502` on chat | Check `OLLAMA_URL` and model name in settings |
| `401` in production | Set `Authorization: Bearer <token>` header |
| `429` | Rate limit hit — wait 60s or raise `RATE_LIMIT_PER_MINUTE` |
| Worker idle | `docker compose logs worker` — requires Redis healthy |
| Compose rejects configuration | Fill all blank secrets in `.env`; development/default secrets fail closed |

---

## Operator CLI (local or container)

```bash
annie doctor
annie grounding --verify
python3 scripts/run_canary_benchmark.py
```

## Release gate

```bash
pip install -e ".[dev,prod]"
pytest -q
./scripts/canary_test.sh
ruff check .
ruff format --check .
bandit -q -r src --severity-level medium
pip-audit --strict -r requirements-prod.lock
python -m build
docker compose config --quiet
docker build -t annie-local:release .
```

Regenerate dependency locks after intentional dependency changes:

```bash
pip-compile requirements-build.in --allow-unsafe --strip-extras --generate-hashes --output-file requirements-build.lock
pip-compile pyproject.toml --extra prod --strip-extras --generate-hashes --output-file requirements-prod.lock
```

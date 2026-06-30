# Annie Local — Run Book

Production and local startup commands for Annie Local v0.3.0.

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

## Mode B — Production (Docker Compose)

Full stack: PostgreSQL, Redis, MinIO (S3), Ollama, API, async worker.

### 1. Configure environment

```bash
cp .env.example .env
# Edit JWT_SECRET, passwords, and CORS_ORIGINS for your deployment
```

### 2. Start all services

```bash
docker compose up -d --build
```

### 3. Pull Ollama model (first time)

```bash
docker compose exec ollama ollama pull llama3.2
```

### 4. Run database migration (if not using init script)

```bash
docker compose exec postgres psql -U annie -d annie -f /docker-entrypoint-initdb.d/001_initial.sql
```

Schema is auto-applied on first Postgres start via `migrations/001_initial.sql`.

### 5. Verify health

```bash
curl -s http://localhost:8787/api/health | python3 -m json.tool
```

### 6. Register and authenticate

```bash
curl -s -X POST http://localhost:8787/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"your-secure-password"}'

export TOKEN="<access_token from response>"

curl -s -X POST http://localhost:8787/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"message":"hello annie"}'
```

### 7. Access services

| Service | URL |
|---------|-----|
| Annie UI | http://localhost:8787 |
| MinIO console | http://localhost:9001 (annie / annie-secret) |
| PostgreSQL | localhost:5432 (annie / annie) |
| Redis | localhost:6379 |

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
| Frontend | Reactive state (`state.js`), API client with JWT + retry (`api-client.js`), validators (`validators.js`), FABLE-5 UI |
| Middleware | JWT auth, CORS, rate limiting (Redis), structured logging, security headers, global error handlers |
| Backend | FastAPI routers → services → repositories; SQLAlchemy async ORM; arq workers |
| Data | PostgreSQL (users, memory, knowledge), Redis (cache + queue), MinIO/S3 (uploads) |
| Safety | Input sanitization, parameterized ORM queries, OWASP headers, env-based secrets |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `engine offline` | `ollama serve` or `docker compose up ollama` + pull model |
| `502` on chat | Check `OLLAMA_URL` and model name in settings |
| `401` in production | Set `Authorization: Bearer <token>` header |
| `429` | Rate limit hit — wait 60s or raise `RATE_LIMIT_PER_MINUTE` |
| Worker idle | `docker compose logs worker` — requires Redis healthy |

---

## Operator CLI (local or container)

```bash
annie doctor
annie grounding --verify
python3 scripts/run_canary_benchmark.py
```

# Replit Preview and Guest Demo

Run Annie Local in [Replit](https://replit.com). **Ollama is required** for chat.
For visitors, set `ANNIE_DEMO_LOCK=true` in the Replit environment before starting.
This serves the [isolated guest interface](DEMO_LOCK.md); operator settings,
knowledge, and documentation routes stay unavailable to guests. Normal local
mode remains the default and should be kept behind operator-only access.

## Import

1. Create a new Repl → **Import from GitHub**
2. URL: `https://github.com/MiMindMendinc/annie-local`
3. Replit reads `.replit` and `main.py` automatically

## Run

Press **Run**, or use the same checked-in entrypoint:

```bash
python main.py
```

The entrypoint launches Annie on `0.0.0.0:8787` and reads `REPLIT_DEV_DOMAIN`
before starting the child process. It adds only `https://<that exact hostname>`
to `CORS_ORIGINS`, preserving existing explicit origins and the selected demo
mode. If no origins were configured, the usual loopback origins are retained.
The variable must contain one bare DNS hostname, without a scheme, port, path,
wildcard, or comma-separated list. Invalid values stop the launch.

Port **8787** is exposed via Replit's webview. Binding `0.0.0.0` does not authorize
arbitrary hosts. Other Replit apps, foreign origins, and forged forwarded-host
headers remain blocked. The guard still applies in guest mode, before its own
session and route restrictions. `annie launch` outside this entrypoint does not
automatically trust Replit environment variables.

### Published deployments and custom domains

[Replit documents `REPLIT_DEV_DOMAIN`](https://docs.replit.com/features/project-setup/configuration)
for the Project Editor; it is unavailable in Deployments. Configure the actual
external HTTPS origin explicitly in the deployment environment, for example:

```text
CORS_ORIGINS=https://your-app.replit.app
ANNIE_DEMO_LOCK=true
```

Replace the example with your deployment's exact origin. Multiple authorized
origins are comma-separated; do not use `*`, suffix wildcards, paths, or `null`.
Restart after changing a hostname or origin. Missing external authorization
leaves external requests blocked; the launcher does not guess a domain from
the app name, incoming requests, or forwarded headers.

The allowlist is a browser request boundary, not authentication. Guest mode is
a single-process demonstration boundary; the public-hosting requirements in
[issue #6](https://github.com/MiMindMendinc/annie-local/issues/6) still apply.

## Ollama on Replit

Replit containers are resource-limited. Options:

| Option | Notes |
|--------|-------|
| Install Ollama in Repl | Needs 8 GB+ RAM for `llama3.2`; use `replit.nix` |
| External Ollama URL | Configure the Ollama endpoint through operator-only settings before enabling guest mode |

Without Ollama, the UI loads but chat shows **engine offline**.

## Replit Agent prompt

```text
Repository: https://github.com/MiMindMendinc/annie-local
Goal: Run Annie Local through its Replit entrypoint with an Ollama backend.

Steps:
1. pip install -e ".[dev]"
2. Start Ollama and pull llama3.2 (or configure its external URL in operator-only settings).
3. Set ANNIE_DEMO_LOCK=true for a visitor demo. For a published deployment, also
   set CORS_ORIGINS to its exact external HTTPS origin.
4. Run: python main.py
5. Verify the page, its assets, and GET /api/health through the external URL.
   In guest mode, POST /api/session with JSON {} before chatting; use its returned
   bearer token for POST /api/chat. Confirm /api/config and /api/knowledge are 404.
6. Confirm foreign Host requests return 400 and foreign Origin writes return 403.

Do not remove hidden grounding substrate. Do not add cloud telemetry.
```

## Files

| File | Purpose |
|------|---------|
| `.replit` | Run command + port config |
| `main.py` | Replit entrypoint |
| `replit.nix` | Optional Nix deps (Python + Ollama) |

## Data

Normal local-mode data is stored in `~/.annie/` inside the container; its lifetime
depends on the Replit environment. Guest conversations use separate temporary
storage and expire or are removed when ended. See [Demo Lock](DEMO_LOCK.md) for
session lifetime and cleanup limits.

## Regression checks

```bash
python -m pytest -q tests/test_replit_launch.py tests/test_local_request_guard.py tests/test_demo_lock.py
```

These checks exercise the launcher configuration and a real loopback HTTP server
with reverse-proxy-style Host/Origin headers in both local and guest modes.
They cover page/assets, writes, guest route restrictions, and foreign-request
rejection. Model responses are test doubles. This is not a live Replit webview,
real-model, or network-isolation certification.

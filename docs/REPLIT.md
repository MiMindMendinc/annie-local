# Replit Deployment

Deploy Annie-5 on [Replit](https://replit.com) for a hosted demo. **Ollama is required** for chat.

## Import

1. Create a new Repl → **Import from GitHub**
2. URL: `https://github.com/MiMindMendinc/annie-local`
3. Replit reads `.replit` and `main.py` automatically

## Run

The Repl runs:

```bash
annie launch --host 0.0.0.0 --port 8787 --no-browser --model llama3.2
```

Port **8787** is exposed via Replit's webview.

## Ollama on Replit

Replit containers are resource-limited. Options:

| Option | Notes |
|--------|-------|
| Install Ollama in Repl | Needs 8 GB+ RAM for `llama3.2`; use `replit.nix` |
| External Ollama URL | Point **cfg** → Ollama endpoint to your own server |

Without Ollama, the UI loads but chat shows **engine offline**.

## Replit Agent prompt

```text
Repository: https://github.com/MiMindMendinc/annie-local
Goal: Run Annie-5 on 0.0.0.0:8787 with Ollama backend.

Steps:
1. pip install -e ".[dev]"
2. Start Ollama and pull llama3.2 (or configure external OLLAMA URL in settings)
3. Run: annie launch --host 0.0.0.0 --port 8787 --no-browser
4. Verify GET /api/health and POST /api/chat

Do not remove hidden grounding substrate. Do not add cloud telemetry.
```

## Files

| File | Purpose |
|------|---------|
| `.replit` | Run command + port config |
| `main.py` | Replit entrypoint |
| `replit.nix` | Optional Nix deps (Python + Ollama) |

## Data

Repl data persists in `~/.annie/` inside the container. Wipe via **mem** drawer or delete the Repl.

# annie-local

**A fully local voice AI companion — FastAPI + Ollama, zero cloud dependencies.**

Annie runs entirely on your machine: local LLM inference via Ollama, private
long-term memory stored as JSONL on your own disk, and a reactive orb UI that
visualizes the assistant's state in real time. Nothing leaves your computer.

## Why this exists

Most "local AI" projects stop at a command line. Annie demonstrates that a
local-first system can have a polished, consumer-grade interface without
giving up the privacy guarantees that make local-first worth doing.

## Features

- **Reactive orb UI** — real-time state visualization (listening, thinking,
  speaking) in a self-contained HTML/JS frontend
- **Fully offline** — Ollama backend (llama3.2, phi3, or any local model)
- **Private memory** — JSONL long-term memory with semantic search; your
  data stays in a folder you control
- **Voice demo** — browser-mic voice loop with no cloud STT/TTS required
- **FastAPI backend** — documented REST API, MIT licensed

## Status

Working prototype, actively developed. See [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md)
and [docs/PRIVACY_AND_SAFETY.md](docs/PRIVACY_AND_SAFETY.md) for the privacy
design and its limits.

## Quick start

```bash
pip install -e .
ollama pull llama3.2
annie launch --model llama3.2
```

Then open: **http://127.0.0.1:8787**

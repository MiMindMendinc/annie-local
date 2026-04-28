# annie-local

**Private local voice AI with a glowing reactive orb.**

Annie Local is an offline-first AI companion interface designed for local models, local memory, and a beautiful real-time orb UI. It gives you a polished browser experience for talking to a local assistant without sending your conversations to a cloud service.

> Built by Michigan MindMend Inc. for privacy-first, local-first AI experimentation.

## Why this exists

Local AI is getting powerful, but most local tools still feel like developer dashboards. Annie Local is meant to feel alive: voice-first, visual, responsive, private, and simple enough for normal people to use.

## Features

- **Reactive glowing orb UI** — visual states for idle, listening, thinking, and speaking
- **Local model backend** — starts with Ollama support
- **Private local memory** — simple local JSONL memory store for session history
- **Browser-based interface** — no Electron required for the first release
- **Offline-first design** — no cloud dependency required for core use
- **Python package + CLI** — install, launch, and iterate quickly
- **Clean extension points** — voice, vision, memory, and backend modules are separated
- **Safe defaults** — user-controlled local model behavior without risky claims or hidden cloud calls

## Quick start

Install from the repo:

```bash
python -m pip install -e .
```

Start Ollama separately and pull a model:

```bash
ollama pull llama3.2
```

Launch Annie:

```bash
annie launch --model llama3.2
```

Then open:

```text
http://127.0.0.1:8787
```

## Commands

```bash
annie launch
annie launch --host 127.0.0.1 --port 8787 --model llama3.2
annie doctor
```

## Project structure

```text
annie-local/
├── README.md
├── LICENSE
├── pyproject.toml
├── src/
│   └── annie/
│       ├── __init__.py
│       ├── cli.py
│       ├── server.py
│       ├── core/
│       │   ├── config.py
│       │   ├── llm.py
│       │   ├── memory.py
│       │   ├── voice.py
│       │   └── vision.py
│       └── ui/
│           ├── index.html
│           ├── app.js
│           └── styles.css
├── examples/
│   └── launch_demo.py
└── tests/
    └── test_config.py
```

## API endpoints

When running locally:

- `GET /api/health` — server status
- `GET /api/config` — active local config
- `POST /api/chat` — send a message to the local model
- `POST /api/memory/search` — search local memory history

## Local model support

The first backend target is Ollama because it is simple and widely used. More backends can be added cleanly through `src/annie/core/llm.py`.

Planned backends:

- Ollama
- llama.cpp server
- vLLM OpenAI-compatible endpoint
- LM Studio local server

## Roadmap

- [x] Repo scaffold
- [x] Local web server
- [x] Reactive orb UI
- [x] Ollama chat backend
- [x] Local JSONL memory store
- [ ] Microphone capture in browser
- [ ] Local speech-to-text adapter
- [ ] Local text-to-speech adapter
- [ ] Vision adapter for multimodal local models
- [ ] Packaged demo assets
- [ ] Installer scripts for Windows, macOS, and Linux

## Responsible positioning

Annie Local is about privacy, ownership, and local control. It does not require cloud APIs, does not phone home by default, and stores memory locally.

## License

MIT License. See `LICENSE` for details.

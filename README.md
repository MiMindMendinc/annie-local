# annie-local

**Fully Local Voice AI Companion with Reactive Glowing Orb**

**100% offline • Private memory • Real-time reactive UI • Beautiful product-grade experience**

> The AI companion that feels alive — running entirely on your machine with zero cloud dependencies.

---

## ✨ What Annie Is

Annie Local is a complete, production-ready local AI companion system featuring a stunning reactive glowing orb interface, private long-term memory, and seamless integration with local LLMs (Ollama).

It’s designed to feel like a real companion — not just another chatbot — while keeping every piece of data 100% private and offline.

## 🚀 Key Features

- **Stunning Reactive Orb UI** — Real-time glowing, pulsing, and emotional state visualization
- **Fully Local** — Runs 100% offline with Ollama (llama3.2, phi3, etc.)
- **Private Memory System** — JSONL-based long-term memory with semantic search
- **Voice Control** — Offline voice demo with browser mic (no cloud STT/TTS required for core experience)
- **FastAPI Backend** — Clean, documented REST API
- **Beautiful Demo** — Self-contained HTML/JS orb that feels like a $10M consumer product

## 📦 Quick Start

```bash
pip install -e .
ollama pull llama3.2
annie launch --model llama3.2
```

Then open: **http://127.0.0.1:8787**

## 🧠 Architecture

```
Browser (Reactive Orb UI)
    ↓
FastAPI Server (Python)
    ↓
Local Ollama Model
    ↓
Private JSONL Memory + Semantic Search
```

## 🎯 Why This Stands Out

Most "local AI" projects are ugly command-line tools. Annie Local proves you can build **beautiful, delightful, consumer-grade experiences** while staying 100% private and offline.

This repo demonstrates:
- Full-stack local AI product development
- Attention to UX and visual polish (rare in AI engineering portfolios)
- Real memory architecture for long-term companions
- Production-ready API design

## 🛠️ Tech Stack

Python • FastAPI • Ollama • HTML/JS • JSONL Memory • WebSockets (for live orb state)

## 📁 What's Included

- Complete working orb UI
- Local memory system with search
- Voice-controlled orb demo (`examples/voicestate-offline.html`)
- Full API documentation
- Performance benchmarking harness

## 🗺️ Roadmap

- [x] Core orb + chat experience
- [x] Private memory system
- [ ] Full voice loop (STT + local TTS)
- [ ] Vision/multimodal support
- [ ] Integration with DominusUltra speed kernel

---

**Built by Lyle Perrien**  
Founder, Michigan MindMend Inc.

*Privacy-first AI that actually feels human.*

MIT License
# Getting Started

This guide gets Annie from zero to talking in under five minutes.

## Requirements

- **Python 3.11+**
- **Ollama** — [ollama.com](https://ollama.com)
- A tool-capable model: `llama3.2`, `llama3.1`, `qwen2.5`, or `mistral-nemo`
- Modern browser (Chrome, Edge, Firefox, Safari)
- Optional: local WOPR voice bridge on port 8123 plus eSpeak NG/eSpeak, or Piper with a local voice model

## Install

### One-liner

```bash
curl -fsSL https://raw.githubusercontent.com/MiMindMendinc/annie-local/main/scripts/install.sh | bash
```

### Manual

```bash
git clone https://github.com/MiMindMendinc/annie-local.git
cd annie-local
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

## Pull a model

```bash
ollama pull llama3.2
```

Verify:

```bash
ollama list
curl http://127.0.0.1:11434/api/tags
```

## Launch

```bash
annie launch --model llama3.2
```

Browser opens to **http://127.0.0.1:8787**.

## First-run diagnostics

```bash
annie doctor
```

Checks:
- Python version
- Ollama reachable
- Models installed
- WOPR voice bridge (optional)
- Data directory `~/.annie/`

If something fails, run:

```bash
annie setup
```

## Using Annie

| Control | Action |
|---------|--------|
| Type + Enter | Send message |
| Shift+Enter | New line |
| Esc | Stop generation |
| **voice** | Toggle spoken replies |
| **mem** | View/edit what Annie remembers |
| **cfg** | Model, temperature, doctrine, endpoints |
| **clr** | Clear conversation + restart session |
| Mic ● | Browser speech input |

## Memory

Annie learns via tools during conversation. View everything in **mem**:

- **Profile** — running summary of who you are
- **Goals** — open tasks Annie tracks
- **Facts** — durable notes
- **Journal** — private reflections

Export JSON or wipe all from the memory drawer.

## Voice (optional)

1. Install a local backend. On Debian, Ubuntu, or Raspberry Pi OS: `sudo apt-get install espeak-ng`
2. Run `python -m annie.wopr_server --self-test`
3. Start the bridge with `python -m annie.wopr_server` (port 8123)
4. In Annie **cfg**, confirm voice URL: `http://127.0.0.1:8123`
5. Toggle **voice** in the header

Piper is also supported when the local `piper` executable and `WOPR_PIPER_MODEL` are configured. If WOPR is down, Annie may offer browser-managed TTS; its locality is unverified.

## Troubleshooting

### "engine offline"

- Start Ollama: `ollama serve`
- Pull a model: `ollama pull llama3.2`
- Check: `annie doctor`

### "no model loaded"

- Open **cfg** → confirm Ollama URL
- Pick a model from the header dropdown

### Tools not working

Use a tool-capable model (`llama3.2` recommended). Some small models reject tool schemas.

### CORS / browser can't reach Ollama

Annie routes through its own server — you should not need browser→Ollama access. If you customized something, reset **cfg** defaults.

## Data deletion

```bash
rm -rf ~/.annie/memory.jsonl ~/.annie/knowledge.json
```

Or use **mem** → **Wipe all** for knowledge only. **clr** clears the current conversation.

## Next

- Read [CHANGELOG.md](../CHANGELOG.md)
- Run `./scripts/canary_test.sh` before distributing a custom build

## Repair a first-run model connection

`annie doctor` reads your saved model and endpoint and prints a MODEL repair block.
`annie setup` detects the Ollama executable, checks the configured endpoint, and asks
for an explicit `yes` before downloading a missing model. It writes settings only
when the configured name resolves to one installed tag, then launches Annie.
If Ollama is missing, install it from https://ollama.com/download.

### Windows PowerShell

Start the daemon in one terminal (if the Ollama desktop app is not already running):

```powershell
ollama serve
```

In another PowerShell terminal, from the repository:

```powershell
ollama pull llama3.2
python -m pip install -e .
annie doctor
annie launch
```

In a third terminal, while Annie runs:

```powershell
curl.exe -s http://127.0.0.1:8787/api/health
```

### Linux

Use the same `ollama pull`, `annie doctor`, and `annie launch` commands after
installing the package with `python -m pip install -e .`. Start `ollama serve` in
a separate terminal if your Ollama service is stopped. Inspect health with
`curl -s http://127.0.0.1:8787/api/health`.

### Container API with Ollama on the Windows host

```text
API in container + Ollama on Windows host
  ollama_url = http://host.docker.internal:11434
```

Container loopback points to the container, not Windows. Configure the operator's
Ollama endpoint accordingly; the host daemon must accept traffic from the container
network. Keep access restricted to that network. Pull models on the host, or set
`OLLAMA_HOST` to the configured endpoint when using the Ollama CLI. The production
Compose file remains a deployment reference, not a finished public multi-user service.

Settings now lists installed tags and accepts a manually entered name. A missing
name requires **Save anyway**. An untagged family with one installed variant resolves
to that variant; multiple variants require choosing an explicit tag. Local routes
are not proof of host network isolation.

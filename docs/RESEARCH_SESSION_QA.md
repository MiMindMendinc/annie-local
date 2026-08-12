# Research Session showcase and QA

The repository includes a deterministic Ollama-compatible demo so the Research Session UI can be reproduced without downloading a model. It binds to loopback, returns fixed content, and is for screenshots and UI checks only.

## Reproduce the showcase

Create an isolated environment and install the demo tooling:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev,demo]"
python -m playwright install chromium
```

Start these commands in separate terminals from the repository root:

```bash
python scripts/mock_ollama.py
```

```bash
mkdir -p /tmp/annie-showcase
annie launch --no-browser \
  --memory-path /tmp/annie-showcase/memory.jsonl \
  --knowledge-path /tmp/annie-showcase/knowledge.json \
  --settings-path /tmp/annie-showcase/settings.json
```

Then open <http://127.0.0.1:8787>, or capture both reference sizes:

```bash
python scripts/capture_demo.py \
  --output docs/assets/research-session.png \
  --mobile-output /tmp/annie-research-session-mobile.png
```

If Chromium is already installed, pass `--chromium-executable /path/to/chromium` instead of downloading Playwright's copy.

Use a real Ollama instance for an end-to-end model showcase. The mock verifies the UI/API contract and measured-metrics rendering; it does not verify model inference.

## Automated checks

```bash
python -m pytest -q
./scripts/canary_test.sh
node --check src/annie/ui/state.js
node --check src/annie/ui/api-client.js
node --check src/annie/ui/app.js
```

## Compact acceptance checklist

- [ ] Orb and voice pill share one phase: `idle`, `listening`, `thinking`, `speaking`, `offline`, or `error`.
- [ ] Stop is enabled only for interruptible phases and aborts browser fetch, recognition, and playback.
- [ ] Model badge reports route and observed availability; it never equates loopback with verified offline operation.
- [ ] Memory badge names the active backend and persistence; structured knowledge can be inspected, exported, deleted, or wiped.
- [ ] Network stays `not verified` unless host isolation is independently proven; remote routes are called out.
- [ ] Browser speech input/output is labeled `locality unverified`; a loopback WOPR bridge is labeled local only when reachable.
- [ ] Latency, token count, and throughput appear only when returned or measured; unavailable values render as an em dash.
- [ ] No CDN, remote font, analytics, or external asset request is made by the packaged UI.
- [ ] Every icon control has an accessible name, visible focus, a 44px target, and a native keyboard path.
- [ ] State changes use a polite live region; the orb is decorative; dialogs have programmatic names and return focus.
- [ ] Layout has no horizontal overflow at 390×844 and remains usable at 200% zoom.
- [ ] `prefers-reduced-motion` removes meaningful animation and high-contrast preferences preserve legibility.

The automated suite covers the API status contract, deterministic state transitions, bundled-asset rule, landmark/control labels, and reduced-motion CSS. Before release, repeat keyboard-only navigation, browser screen-reader output, 200% zoom, and real-device microphone permission tests.

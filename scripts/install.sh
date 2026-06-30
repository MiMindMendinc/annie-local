#!/usr/bin/env bash
# Annie Local — one-command bootstrap
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

echo ""
echo "  ANNIE-5 · local install"
echo "  ─────────────────────────"
echo ""

# Python check
if ! command -v python3 >/dev/null 2>&1; then
  echo "✗ python3 not found. Install Python 3.11+ first."
  exit 1
fi

PY_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "✓ Python $PY_VERSION"

# venv (optional but recommended)
if [[ ! -d .venv ]]; then
  echo "→ Creating .venv ..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "→ Installing annie-local ..."
python3 -m pip install --upgrade pip -q
python3 -m pip install -e ".[dev]" -q

echo ""
echo "→ Checking Ollama ..."
if command -v ollama >/dev/null 2>&1; then
  echo "✓ Ollama CLI found"
  if curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "✓ Ollama daemon running"
    MODELS="$(curl -sf http://127.0.0.1:11434/api/tags | python3 -c 'import sys,json; d=json.load(sys.stdin); print(len(d.get("models",[])))' 2>/dev/null || echo 0)"
    echo "  Models installed: $MODELS"
    if [[ "$MODELS" == "0" ]]; then
      echo "→ Pulling llama3.2 (recommended) ..."
      ollama pull llama3.2 || echo "  (pull manually: ollama pull llama3.2)"
    fi
  else
    echo "⚠ Ollama not running. Start it: ollama serve"
    echo "  Then: ollama pull llama3.2"
  fi
else
  echo "⚠ Ollama not installed. Get it at https://ollama.com"
  echo "  Then: ollama pull llama3.2"
fi

echo ""
echo "→ Running tests ..."
python3 -m pytest -q
./scripts/canary_test.sh

echo ""
echo "  ✓ Annie Local is installed."
echo ""
echo "  Launch:"
echo "    source .venv/bin/activate"
echo "    annie launch --model llama3.2"
echo ""
echo "  Or:"
echo "    annie doctor"
echo ""

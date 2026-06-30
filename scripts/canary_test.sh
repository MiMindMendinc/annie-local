#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pytest -q tests/test_canary_substrate.py tests/test_substrate.py tests/test_chat.py

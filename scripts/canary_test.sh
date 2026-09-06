#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/run_canary_benchmark.py
python3 -m pytest -q tests/test_canary_substrate.py tests/test_substrate.py tests/test_chat.py tests/test_grounding_audit.py tests/eval/test_plan_contract.py

# Canary Benchmark Results

**Last run:** 2026-08-12 00:20 UTC
**Overall:** PASS

## Summary

| Suite | Pass | Total | Rate |
|-------|------|-------|------|
| Harm triggers → redirect (strike 1) | 7 | 7 | 7/7 |
| Safe replies (no false positive) | 11 | 11 | 11/11 |
| Repeat harm → restart (strike 2) | 2 | 2 | 2/2 |

## Method

- Regex + heuristic scan on **model output** (not user input)
- First strike: redirect, no restart
- Second strike: session restart
- See [GROUNDING.md](GROUNDING.md) for architecture (rules not published)

## Failures

No failures.

## Reproduce

```bash
python3 scripts/run_canary_benchmark.py
./scripts/canary_test.sh
```

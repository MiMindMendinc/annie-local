# Speed Kernel Lab

DominusUltra is an experimental performance research path for Annie Local. Runtime integration is still experimental, and benchmark claims must stay separate from the stable user-facing app.

## What this branch does

- Adds `src/annie/core/speed_kernel.py`
- Adds `--speed-kernel` CLI detection
- Adds `--speed-kernel-backend dominus-ultra`
- Reports speed-kernel status from `/api/health`
- Reports speed-kernel metadata from `/api/chat`
- Adds `benchmarks/run_speed_kernel.py`

## Benchmark scope

This benchmark measures the standard Ollama generation path (baseline).
The DominusUltra kernel path is not yet exercised by this script.

Run the benchmark harness:

```bash
python -m benchmarks.run_speed_kernel --model llama3.2 --runs 5
```

Passing `--speed-kernel` is accepted for CLI compatibility, but the harness still runs baseline mode only until the DominusUltra path is actually wired in.

## What this branch does not claim

This branch does **not** claim that Annie Local chat inference is accelerated yet.

It does not claim:

- production-grade acceleration
- faster-than-baseline performance without benchmark proof
- verified speedups across hardware
- real-time LLM backend replacement
- GPU support on machines without the required local stack

## Why this exists

Annie Local is the user-facing local AI interface.
DominusUltra is the low-level performance research layer.

This branch creates a safe bridge between them:

```text
Annie Local UI
  ↓
Local model backend
  ↓
Speed Kernel Lab adapter
  ↓
DominusUltra / future performance experiments
```

## How to try it

Install Annie Local from this branch:

```bash
python -m pip install -e .
```

Launch normally:

```bash
annie launch --model llama3.2
```

Launch with experimental speed-kernel detection:

```bash
annie launch --model llama3.2 --speed-kernel
```

Check status:

```bash
curl http://127.0.0.1:8787/api/health
```

If `dominus_ultra` is importable on your `PYTHONPATH`, the adapter will report it as detected.

## Next engineering steps

1. Convert DominusUltra into an installable Python package.
2. Wire a real DominusUltra execution path into a separate benchmark.
3. Record hardware, software versions, shapes, dtype, baseline, and max error.
4. Only then discuss measured performance differences.

## Credibility rule

Performance claims must be backed by reproducible benchmark logs. Until then, this stays a lab path.

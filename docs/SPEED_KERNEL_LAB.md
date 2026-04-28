# Speed Kernel Lab

This branch experiments with connecting Annie Local to the broader Michigan MindMend speed-kernel work.

The first target is **DominusUltra**, an educational Triton attention-kernel project focused on fused RoPE, causal attention, and GQA-style head mapping.

## What this branch does

- Adds `src/annie/core/speed_kernel.py`
- Adds `--speed-kernel` CLI detection
- Adds `--speed-kernel-backend dominus-ultra`
- Reports speed-kernel status from `/api/health`
- Reports speed-kernel metadata from `/api/chat`

## What this branch does not claim

This branch does **not** claim that Annie Local chat inference is accelerated yet.

It does not claim:

- production-grade acceleration
- faster-than-FlashAttention performance
- verified Triton kernel speedups
- real-time LLM backend replacement
- GPU support on machines without CUDA/Triton/PyTorch

## Why this exists

Annie Local is the user-facing local AI interface.
DominusUltra is the low-level GPU-kernel learning and experimentation layer.

This branch creates a safe bridge between them:

```text
Annie Local UI
  ↓
Local model backend
  ↓
Speed Kernel Lab adapter
  ↓
DominusUltra / future GPU kernel experiments
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
2. Add a small non-runtime benchmark command such as `annie kernel-bench`.
3. Run GPU-only benchmarks outside normal Annie chat flow.
4. Record hardware, CUDA, PyTorch, Triton, shape, dtype, baseline, and max error.
5. Only then wire a real acceleration path into model-serving experiments.

## Credibility rule

Performance claims must be backed by reproducible benchmark logs. Until then, this stays a lab branch.

# annie-local

**Private local voice AI with a glowing reactive orb.**

Annie Local is an offline-first AI companion interface designed for local models, local memory, and a beautiful real-time orb UI.

## Features

- Reactive glowing orb UI
- Local model backend with Ollama support
- Private local memory
- Browser-based interface
- Offline-first design
- Python package and CLI

## Performance Lab (Experimental)

Want to test performance work? Check out the experimental performance branch.

It introduces DominusUltra as a separate validation path. Keep it separate from main until benchmark results are reproducible.

To test:

```bash
git checkout speed-kernel-lab
python -m pip install -e .
annie launch --model llama3.2 --speed-kernel
```

Benchmark script lives at `benchmarks/run_speed_kernel.py`.

## Quick start

```bash
python -m pip install -e .
ollama pull llama3.2
annie launch --model llama3.2
```

Open `http://127.0.0.1:8787`.

## License

MIT License. See `LICENSE` for details.

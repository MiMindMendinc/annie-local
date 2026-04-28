# NOTE: This is a baseline benchmark only.
# DominusUltra kernel integration is still experimental.
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

DEFAULT_PROMPT = "Explain why local-first AI matters in one clear paragraph."


@dataclass(frozen=True)
class RunResult:
    run: int
    mode: str
    ttft_s: float
    total_s: float
    tokens_generated: int
    tok_per_s: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark the baseline Ollama generation path.")
    parser.add_argument("--model", default="llama3.2", help="Ollama model name.")
    parser.add_argument("--runs", type=int, default=5, help="Number of measured runs.")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434", help="Ollama base URL.")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Prompt to use for every run.")
    parser.add_argument("--speed-kernel", action="store_true", help="Accepted for compatibility; benchmark still runs base mode only.")
    return parser.parse_args()


def post_json(url: str, payload: dict[str, Any]):
    data = json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    return urlopen(request, timeout=300)


def count_tokens_from_response(raw: dict[str, Any], text: str) -> int:
    eval_count = raw.get("eval_count")
    if isinstance(eval_count, int) and eval_count > 0:
        return eval_count
    return max(1, len(text.split()))


def run_once(run_id: int, model: str, ollama_url: str, prompt: str) -> RunResult:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }
    start = time.perf_counter()
    first_token_time: float | None = None
    chunks: list[str] = []
    final_raw: dict[str, Any] = {}

    try:
        with post_json(f"{ollama_url.rstrip('/')}/api/chat", payload) as response:
            for line in response:
                if not line.strip():
                    continue
                raw = json.loads(line.decode("utf-8"))
                final_raw = raw
                content = (raw.get("message") or {}).get("content") or ""
                if content and first_token_time is None:
                    first_token_time = time.perf_counter()
                if content:
                    chunks.append(content)
                if raw.get("done") is True:
                    break
    except URLError as exc:
        raise RuntimeError(f"Could not reach Ollama at {ollama_url}: {exc}") from exc

    end = time.perf_counter()
    text = "".join(chunks)
    total_s = max(end - start, 1e-9)
    ttft_s = (first_token_time - start) if first_token_time is not None else total_s
    tokens = count_tokens_from_response(final_raw, text)
    tok_per_s = tokens / total_s
    return RunResult(run=run_id, mode="base", ttft_s=ttft_s, total_s=total_s, tokens_generated=tokens, tok_per_s=tok_per_s)


def markdown_table(results: list[RunResult]) -> str:
    lines = [
        "| Run | Mode | TTFT (s) | Total (s) | Tokens | Tok/s |",
        "| ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for result in results:
        lines.append(
            f"| {result.run} | {result.mode} | {result.ttft_s:.3f} | {result.total_s:.3f} | "
            f"{result.tokens_generated} | {result.tok_per_s:.2f} |"
        )
    return "\n".join(lines)


def print_summary(results: list[RunResult]) -> None:
    avg_ttft = statistics.mean(r.ttft_s for r in results)
    avg_total = statistics.mean(r.total_s for r in results)
    avg_tokens = statistics.mean(r.tokens_generated for r in results)
    avg_toks = statistics.mean(r.tok_per_s for r in results)
    print("\n## Averages\n")
    print("| Metric | Average |")
    print("| --- | ---: |")
    print(f"| TTFT | {avg_ttft:.3f} s |")
    print(f"| Total time | {avg_total:.3f} s |")
    print(f"| Tokens generated | {avg_tokens:.1f} |")
    print(f"| Throughput | {avg_toks:.2f} tok/s |")


def main() -> int:
    args = parse_args()
    if args.runs <= 0:
        print("--runs must be greater than zero", file=sys.stderr)
        return 2

    print("# Annie Local Baseline Benchmark\n")
    print("This benchmark measures the standard Ollama generation path only.\n")
    if args.speed_kernel:
        print("DominusUltra kernel path not yet implemented in this benchmark harness — running base mode only.\n")

    results = [run_once(index + 1, args.model, args.ollama_url, args.prompt) for index in range(args.runs)]
    print(markdown_table(results))
    print_summary(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

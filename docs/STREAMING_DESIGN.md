# Streaming grounding design and acceptance

Reviewed during the PR #19 verification pass on 2026-09-07. The implementation
and adversarial tests below support this design; target-browser acceptance is
still required. No independent reviewer or physical-device signoff is implied.

## Display and finalization boundaries

1. Ollama content enters a private engine callback. Provider progress events
   contain counts, never raw text or tool arguments.
2. `DisplayPrefixGuard` applies partial matching to the same expressions used
   by the grounding substrate. It releases only text preceding the earliest
   complete or still-possible expression. It does not apply refusal/support
   exemptions or wait for a human target before holding a possible expression.
   Matching uses a length-preserving policy view to retain Python `re` word,
   whitespace, and ASCII-letter case semantics, including dotless I and combining
   marks. Original Unicode text is displayed unchanged. Each possible start is
   checked in order; a later full match cannot displace an earlier partial one.
3. Ordinary unambiguous text can therefore reach the browser on its first
   content chunk, before provider completion. Ambiguous beginnings may wait
   for more text, and a complete candidate expression holds the remaining turn
   until the final check. A 25 ms scan budget latches to buffering on timeout.
4. The original whole-turn grounding check remains authoritative. Tool calls
   execute only after their completed turn passes it. A tool preamble is
   removed before the next turn; tool payloads are not display deltas.
5. A completed reply is checked before assistant-memory persistence. Planning
   retains its non-streaming JSON-schema contract and read-only tool policy.
6. The UI displays provisional text using `textContent`. It creates no transcript
   export entry, app copy button, or speech for that preview. `replace` clears
   the preview; `done` commits exactly one authoritative response. Errors and
   cancellation remove provisional text.

This preserves the existing detection rules and strike/audit/restart behavior.
The repeat-trigger signal **wording** was corrected: it now describes the reset
and retained notes/goals instead of returning the previous jokey harm phrase.
The default care instructions were not changed.

The early display contract is narrower than whole-response validation: a harmless
prefix can be visible before a later redirect. It is not a promise that every
raw first token is immediately releasable, nor that these heuristic rules detect
all harmful content. The delayed suffix is necessary to avoid leaking a trigger
split across tokens. Whole-response exemptions are not assumed from a prefix.

## Transport and cancellation

| SSE event | Meaning |
| --- | --- |
| `progress` | Provider activity without raw content |
| `delta` | Append a prefix admitted by the display guard |
| `reset` | Discard a tool-turn preamble |
| `replace` | Discard the preview in preparation for the authoritative reply |
| `done` | Commit the final checked response and its metrics; terminal event |
| `error` | Discard the preview and report the request failure; terminal event |

The queue remains bounded at eight events. Disconnect cancels the generation
task and closes the provider stream. The browser checks cancellation before
processing buffered events, after a late completion, and after voice loading;
an aborted voice request cannot start browser fallback.

Cancellation does not roll back a user's already-persisted input or a tool action
completed in an earlier validated turn. The claim tested here is that an
in-flight provider reply is not saved as an assistant response or spoken after
cancellation. A disconnect arriving after server finalization does not roll
back an already committed, checked reply. The UI still ignores late completion
and speech after its request has been aborted.

## Verification

- Every two-way partition plus single-character delivery of 22 expression cases,
  including whitespace, Unicode, and a distant human target.
- Regressions for combining-mark/joiner word boundaries, dotless-I case matching,
  an earlier partial expression followed by a complete expression, and a complete
  candidate that later becomes a different word.
- Immediate benign content, ambiguous-prefix resolution, word boundaries,
  context exemptions withheld until completion, and timeout buffering.
- A controlled provider barrier proves a delta arrives while generation is
  still incomplete and before assistant-memory persistence.
- Split-trigger redirects, one audit event per trigger, rejected tool turns,
  tool-preamble reset, safe repeat-trigger restart, and knowledge retention.
- Malformed provider frames, disconnect, truncated streams, terminal `done`,
  buffered-event cancellation, late completion, and late voice response.
- Real Uvicorn HTTP/SSE with Ollama 0.33.3 and both `llama3.2:latest` and
  `llama3.1:8b`: actual first provider content, first client text, completion,
  and disconnect cancellation. These CPU observations are not benchmarks.

The implementation review caught two unsafe assumptions before publication:
the two matching engines have different Unicode semantics, and a partial search
can prefer a later complete match. Both were corrected and regression tested.
An exhaustive local comparison also confirmed word, whitespace, and ASCII-letter
class agreement across all 1,114,112 Unicode code points. The policy projection
supports the current grammar (ASCII literals, word boundaries, whitespace, and
`[^.]`); changing that grammar requires reviewing the projection too.

Recorded results: [default model](evidence/live-streaming-llama32-2026-09-07.json),
[alternate model](evidence/live-streaming-llama31-2026-09-07.json), and
[browser QA](evidence/browser-qa-2026-09-07.json). Each API run includes source
file hashes and actual model inventory. The alternate run uses an isolated
inventory containing only `llama3.1:8b`.

The cloud Chrome pass verified repair/ready display, offline goal saving,
draft retention through model selection, and the settings focus fix. Its
restricted runtime could list models but could not load Ollama's inference
backend. **No successful browser generation, browser Stop/Esc acceptance,
physical Safari, or assistive-technology pass is claimed.**

## Reproduce

With a running local Ollama and an installed model, from the candidate checkout:

```sh
python -m pip install -e ".[dev,prod]"
ANNIE_MODE=local python scripts/verify_live_streaming.py \
  --model llama3.2 --output streaming-evidence.json
```

The verifier starts an ephemeral Annie HTTP server with temporary synthetic
data. It downloads no models and does not change existing Annie settings or
memory. To test the exact alternate scenario, use an Ollama inventory containing
only `llama3.1:8b`, and add `--model llama3.1:8b --alternate-only`.

The owner authorized integrating this documented design after the verification
limits were disclosed on 2026-09-12. Finish the target-device checks in
[DEVICE_QA.md](DEVICE_QA.md) before declaring release readiness.

Implementation references: [Ollama streaming](https://docs.ollama.com/capabilities/streaming)
and the `regex` package's [partial matching and timeout support](https://pypi.org/project/regex/).
The Unicode projection follows [Python's documented regular-expression semantics](https://docs.python.org/3.12/library/re.html).

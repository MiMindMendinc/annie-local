# Annie Local Status

**v0.4.0 candidate — unreleased.** Includes the work from PRs #17 → #18 → #19.
Real local-model testing found and corrected planning failures that mocked tests
had missed. Guarded early text and real HTTP timing/cancellation now pass.
Physical device, remaining accessibility, and real-model target-browser
generation/streaming acceptance remain open.

The 2026-09-12 integration includes merged PR #21 and guest isolation from main.
It fixes repair-detail leakage into guest health. Current local evidence is
329 Python tests, 31 Node tests, and all 20 canaries passing; the target-browser
and physical-device gates remain open. See the current [integration record](evidence/integration-2026-09-12.json).

## Candidate evidence

| Area | Current evidence and limit |
| --- | --- |
| Notes and goals | Save without a model; real-model planning and model loss preserve saved facts and goals. |
| Local inference | Real Ollama chat and default tag resolution checked through the application API. |
| Planning | Ollama receives the Plan JSON schema; output is validated, grounding stays active, and write tools remain blocked. |
| Recovery | The exact llama3.2-configured / only-llama3.1:8b-installed scenario passed through API and cloud Chrome selection/save. |
| Streaming | Admitted prefixes arrive before provider completion; ambiguous suffixes wait for final grounding. Both real models pass HTTP cancellation. |
| UI | Desktop repair/ready captures, draft/goal recovery, and settings focus verified; real browser generation, physical Safari, and assistive technology remain open. |
| Voice | WOPR implementation and CI speech self-test; browser-managed voice locality remains unverified. |
| Packaging and security | Python 3.11/3.12, UI checks, release gate, and CodeQL run in CI. |
| Public hosting | Hardened Compose reference; operational and review gates remain in issue #6. |

The [readiness report](RELEASE_READINESS.md) records the exact source commit,
model, environment, results, and remaining checks. The original smoke run used
ASGI TestClient; the follow-up measures actual Uvicorn HTTP/SSE against real
Ollama. Both use Linux CPU inference and synthetic data. Neither is a result
from the user's physical device.

## Release requirements still open

Complete [DEVICE_QA.md](DEVICE_QA.md), including physical Safari, assistive
technology, successful real-model browser streaming/Stop/Esc, and target-device
captures. The [grounding-compatible implementation](STREAMING_DESIGN.md), HTTP
proof, and alternate-model recovery are available. Keep the
candidate untagged until the release acceptance requirements are met. The owner
requested integration after the remaining checks were disclosed; merging the
code does not constitute a pass on those checks.

## Runtime boundaries

Configured local routes do not verify host network isolation. Browser speech may
use browser-managed services. The project does not claim clinical validation,
regulatory compliance, reviewed public multi-user hosting, or attachment uploads.
The S3-compatible service foundation has no enabled attachment API or UI.

## Operator notes

Default conversation and knowledge storage are `~/.annie/memory.jsonl` and
`~/.annie/knowledge.json`; optional production storage uses PostgreSQL. Saved
context is sent to the configured model endpoint when knowledge tools are enabled.

Grounding substrate logs locally to `~/.annie/.substrate.ndjson` (hash-chained,
mode 0600), outside the UI and API. Run `./scripts/canary_test.sh` before custom
builds. See [GROUNDING.md](GROUNDING.md) and [RUNBOOK.md](RUNBOOK.md).

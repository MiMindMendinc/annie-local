# Annie Local Status

**v0.4.0 candidate — unreleased.** Work remains in the draft stack #17 → #18 → #19.
Real local-model testing found and corrected planning failures that mocked tests
had missed. Physical device, accessibility, ready-state browser, and immediate
text-streaming requirements remain open.

## Candidate evidence

| Area | Current evidence and limit |
| --- | --- |
| Notes and goals | Save without a model; real-model planning and model loss preserve saved facts and goals. |
| Local inference | Real Ollama chat and default tag resolution checked through the application API. |
| Planning | Ollama receives the Plan JSON schema; output is validated, grounding stays active, and write tools remain blocked. |
| Recovery | Missing-model diagnostics and selecting an installed tag checked through the API. |
| Streaming | Provider progress and cancellation implemented; text waits for whole-response grounding. |
| UI | Automated checks and desktop repair capture; physical Safari and assistive technology checks pending. |
| Voice | WOPR implementation and CI speech self-test; browser-managed voice locality remains unverified. |
| Packaging and security | Python 3.11/3.12, UI checks, release gate, and CodeQL run in CI. |
| Public hosting | Hardened Compose reference; operational and review gates remain in issue #6. |

The [readiness report](RELEASE_READINESS.md) records the exact source commit,
model, environment, results, and remaining checks. The real-model run used a Linux
CPU environment and synthetic data through ASGI TestClient with real Ollama HTTP
requests. It is not a result from the user's device or a browser interaction test.

## Release requirements still open

Complete [DEVICE_QA.md](DEVICE_QA.md), including physical Safari, assistive
technology, the alternate-model scenario, and target-browser captures. Immediate
first-token text display requires a grounding-compatible implementation. Keep the
candidate unmerged and untagged until the acceptance requirements are met.

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

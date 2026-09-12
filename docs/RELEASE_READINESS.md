# v0.4.0 candidate readiness

**Unreleased; the PR stack remains draft.** The follow-up below implements early
text delivery with grounding and adds real HTTP proof. Physical-device,
accessibility, and successful generation/streaming in a working target browser
remain open. This report does not certify the whole project as finished or
establish public hosting readiness.

## Current integration — 2026-09-12

The complete candidate now includes main through `b5ae267` (merged PR #21),
the request Host/Origin boundary, the exact Replit startup origin, and the
isolated guest demo from PR #23. The stacked branches were updated in order
without rewriting their history.

Integration reproduced a guest privacy regression: model repair diagnostics
would include the configured model and backend endpoint in guest health.
Guest model health now projects only coarse readiness and locality fields.
Ready, missing-model, and empty-inventory cases verify the same boundary.
Operator repair diagnostics remain available in normal local mode.

Current local verification: **329 Python tests, 31 Node tests, all 20 grounding
canaries and their 27 supporting tests passed**, with no failures or skips.
Ruff lint/format, the medium/high Bandit gate, the production dependency audit,
and wheel/sdist builds passed. Eight request-guard, streaming, and guest source
or asset files match the source bytes in both distributions. One upstream
Starlette/AnyIO deprecation warning remains. CI and Security now also run for
the two stacked PR base branches. See [the integration record](evidence/integration-2026-09-12.json).

The supported cloud browser rejected this candidate's loopback page with
`net::ERR_BLOCKED_BY_CLIENT`. No new browser, real-model, physical Safari,
screen-reader, or live Replit pass is claimed. All target-device and
provisional-display acceptance gates below remain open; the stack stays draft.
The September 6–7 real-model evidence remains historical at its recorded source.

## Streaming follow-up — 2026-09-07

- Guarded text prefixes now flow through the API into a provisional browser reply.
  Whole-response validation remains the commit boundary. See [STREAMING_DESIGN.md](STREAMING_DESIGN.md).
- The local automated suite passes **211 Python tests and 25 Node tests** with
  no failures or skips, plus all 20 grounding canaries. Lint, formatting,
  dependency audit, and static security checks pass. Current GitHub CI must also
  be green on the published candidate head before merge.
- Real Uvicorn HTTP/SSE tests pass for Ollama 0.33.3 with `llama3.2:latest` and
  `llama3.1:8b`, including first text before provider completion and disconnect
  cancellation without a saved assistant reply. Actual timings and source hashes
  are in the linked [default](evidence/live-streaming-llama32-2026-09-07.json) and
  [alternate](evidence/live-streaming-llama31-2026-09-07.json) records. Cold model
  startup is substantially slower than a warmed request; these are observations.
- The exact alternate inventory/picker scenario passed in cloud Chrome; a draft
  and saved goal survived recovery. New repair and ready captures are in DEVICE_QA.
- Browser QA found Tab escaping the settings dialog; wrapping and focus return
  now pass after the fix. A late-response/voice cancellation race was also fixed.
- The old repeat-trigger signal wording was replaced with a plain reset message;
  trigger logic, audit, restart, and knowledge preservation remain tested.

**Still blocks the requested merge:** physical Safari/iPhone, the remaining
accessibility checks, and successful real-model browser chat/planning plus
first-text/Stop/Esc acceptance. The cloud preview's inference backend failed to
load; its ready display is not a successful generation result. Review the full
#17 → #18 → #19 stack, explicitly accept the provisional-display grounding
boundary, and check current CI before changing draft state. No independent PR
approval is recorded at the time of this verification.

The sections below retain the original 2026-09-06 evidence at its stated source.

## Verified source and environment

| Item | Recorded value |
| --- | --- |
| Date | 2026-09-06 UTC |
| Application source | `10742443c98a720cd819bd288d85b42053eaee74` |
| Environment | Linux x86_64, 9 reported CPUs, CPU inference |
| Ollama | 0.33.3, loopback endpoint `http://127.0.0.1:11434` |
| Configured model | `llama3.2`, resolved to `llama3.2:latest` |
| Model | 3.2B, GGUF, Q4_K_M, 2,019,393,189 bytes |
| Model digest | `a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72` |
| Method | ASGI TestClient calling the real Ollama HTTP service |
| Data | Temporary storage containing synthetic notes and goals |

Ollama was installed from its official Linux distribution; cloud features were
disabled for the run with `OLLAMA_NO_CLOUD=1`. Model installation required a
download. Neither that setting nor loopback routing verifies host network isolation.

The [recorded JSON](evidence/live-ollama-2026-09-06.json) contains actual Ollama
version and model inventory, unavailable/ready health responses, streamed chat
events, rendered plans, and the outcomes below. Temporary data paths were replaced
with `<temporary-test-data>`. The run did not use a browser, physical phone,
microphone, speaker, or screen reader.

## Real-model results

| Check | Result |
| --- | --- |
| Health before Ollama starts reports unavailable | Pass |
| Offline streaming request returns the repair response | Pass, HTTP 502 |
| Notes and goals save while the model is down | Pass, HTTP 201 |
| Default model name resolves to the installed `:latest` tag | Pass |
| Real chat completes with text and a done event | Pass |
| Direction returns a validated plan | Pass |
| Clarity returns a validated plan | Pass |
| Planning preserves saved facts and goals | Pass |
| A missing configured model reports unavailable | Pass |
| Selecting an installed model restores readiness | Pass |
| Stopping the model preserves saved notes and goals | Pass |

All **11 checks passed**. The synthetic Direction request asked for a next step
on organizing a desk in fifteen minutes. Clarity asked for help organizing a
reusable notebook for small home projects. Their rendered outputs have one
unchecked marker per checklist item. This smoke run verifies those responses;
it does not establish general model quality. Recorded timings are observations
from this CPU run, not performance benchmarks.

## Failures found and corrected

At `f9d280fde527aa8e52a82b4b27caebfdf13795f6`, chat worked with the real default
model but both planning requests returned HTTP 502 because the output did not
satisfy the Plan contract. The existing mocked tests had supplied valid JSON.

- `8572d40a7d872169c10ddc0eceb19746a639888d` sends the same Pydantic Plan JSON
  schema to Ollama through `format`. Regular chat keeps its existing format;
  grounding validation and planning write-tool rejection remain active. Tests
  cover both tool support and the fallback that retries without tools.
- `10742443c98a720cd819bd288d85b42053eaee74` removes model-supplied list and
  checkbox prefixes before rendering, preventing doubled checkboxes. Empty
  marker-only entries are rejected.

Ollama documents JSON-schema constraints in its
[structured outputs guide](https://docs.ollama.com/capabilities/structured-outputs).

## Automated verification

On the recorded source commit, a fresh editable install with development and
production dependencies passed **166 Python tests** and **19 Node tests**, with
no test failures or skips. Pytest reported one dependency deprecation warning
from Starlette's use of the AnyIO BlockingPortal alias.

[CI run 34015244134](https://github.com/MiMindMendinc/annie-local/actions/runs/34015244134)
passed Python 3.11 and 3.12, the UI checks, substrate canary, and release gate.
The release gate includes lint/format, Bandit, dependency audit, distributions,
JavaScript validation, a real espeak-ng speech self-test, and container build.
[Security run 34015244124](https://github.com/MiMindMendinc/annie-local/actions/runs/34015244124)
passed CodeQL. Those CI results are separate from the real Ollama run above.

To repeat automated checks from the candidate checkout:

```sh
python -m pip install -e ".[dev,prod]"
python -m pytest -q
node --test tests/ui_*.test.js
bash scripts/canary_test.sh
```

To repeat local-model acceptance, follow the first-run sequence in
[DEVICE_QA.md](DEVICE_QA.md) with isolated test data. Record the exact source,
Ollama version, model digest, health responses, and outputs. The recorded run
used the application factory with temporary `memory_path`, `knowledge_path`,
and `settings_path`, leaving existing user data untouched.

## Remaining release requirements

- Physical Safari at 390 × 844 and 428 × 926, including software keyboard and
  safe-area behavior.
- Keyboard, assistive technology, enlarged text, contrast, reduced motion, and
  cancellation behavior on the target setup.
- Actual ready-state and repair-state captures on the physical target device.
  New cloud Chrome captures and alternate-model recovery are available; they
  do not establish a physical-device pass.
- Real-model browser chat/planning, first-text delivery, and Stop/Esc acceptance.
  The guarded implementation and actual HTTP timing/cancellation evidence now
  exist; the restricted cloud browser setup could not load its inference backend.
- Review the complete #17 → #18 → #19 stack and evidence before merge and tag.

The historical 2026-09-06 run had no browser pass. The 2026-09-07 cloud browser
observations are recorded separately above. Optional public multi-user operations
remain tracked separately in
[issue #6](https://github.com/MiMindMendinc/annie-local/issues/6).

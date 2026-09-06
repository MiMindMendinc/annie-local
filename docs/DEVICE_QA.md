# Device and release QA

Status: candidate work, not a WCAG conformance certification or an Excellent release.
Checks below must be recorded on the actual target devices before release.

| Viewport | Required check | Evidence status |
| --- | --- | --- |
| 390 × 844 | Safari, keyboard open/close, draft visible, no horizontal scroll | Pending physical device |
| 428 × 926 | Safari, safe area, composer and dialog controls reachable | Pending physical device |
| 1363 × 936 | Desktop repair panel, draft/retry, settings focus, disabled send/mic | Browser checked 2026-09-06 |

## Keyboard and assistive technology

- [ ] Tab from Skip to workspace through the header, repair actions, memory and composer.
- [ ] Confirm a visible focus indicator; dialogs trap focus and return it to the opener.
- [ ] Choose installed model focuses Model; its installed/missing result is announced.
- [ ] Disabled Direction/Clarity skip Tab, expose aria-disabled, and have visible reasons.
- [ ] A screen reader announces “Model offline. Memory still works.” on loss of readiness.
- [ ] Read all three badges: Model, Memory, and Network, including the unverified qualifier.
- [ ] Test 200% text enlargement, high contrast, and every active control's 44px target.
- [ ] With reduced motion enabled, glass animation and card hover translation stop.
- [ ] Stop and Esc cancel generation; no reply or speech begins after cancellation.

## First-run acceptance on real Ollama

- [x] Record the Linux CPU environment, Ollama version, and `ollama list` in the [readiness report](RELEASE_READINESS.md).
- [x] With Ollama stopped, verify unavailable health, repair response, and working notes/goals APIs.
- [x] Pull llama3.2, verify default-name resolution to llama3.2:latest, and complete real chat.
- [x] Capture actual unavailable and ready `/api/health` JSON.
- [x] Check real Direction and Clarity outputs against the plan contract and preserve saved knowledge.
- [x] Verify missing-model diagnostics, installed-tag selection, and memory retention after model loss through the API.
- [ ] Verify repair mode in the target browser: send/mic off and memory capture works.
- [ ] Verify ready mode in the target browser: Model: local and enabled planning/chat.
- [ ] With only llama3.1:8b installed and llama3.2 configured, select the installed tag and save.
- [ ] Attach ready and repair screenshots from the actual target setup to the PR.

The recorded run uses ASGI TestClient with real loopback HTTP requests to Ollama
and synthetic notes/goals. It does not establish browser microphone/speaker behavior,
physical phone behavior, assistive-technology support, or network isolation. The
cloud browser could not open this run's local preview. Automated mock-server tests
separately exercise schema and tool enforcement; they are not real-model evidence.

## Streaming acceptance limitation

The implementation reads Ollama's real NDJSON stream, reports generation progress,
and closes the provider stream on cancellation. It retains the existing whole-response
grounding check before releasing text. Immediate first-token text display is **not**
implemented. Do not label the entire A5 acceptance complete or tag Excellent on this basis.

## Viewport implementation

The app shell follows `visualViewport.height` and `offsetTop` on resize/scroll,
with a CSS dynamic-viewport fallback. This is implemented and desktop checked;
it is not proof of iOS software-keyboard behavior. No physical phone screenshot
or screen-reader conformance result was produced in this environment.

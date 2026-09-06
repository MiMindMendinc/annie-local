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

- [ ] Record hardware, operating system, Ollama version, and `ollama list`.
- [ ] With Ollama stopped, capture repair mode: send/mic off, memory capture works.
- [ ] Pull llama3.2, retry health, capture Model: local and enabled planning/chat.
- [ ] With only llama3.1:8b installed and llama3.2 configured, select the installed tag and save.
- [ ] Attach actual `/api/health` JSON and both ready/repair screenshots to the PR.
- [ ] Check real model Direction and Clarity outputs against the plan contract.

The automated mock-server evaluation tests schema and tool enforcement, not real-model
quality. Ollama is absent in the execution environment used for this candidate.

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

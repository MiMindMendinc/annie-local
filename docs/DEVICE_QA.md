# Device and release QA

Status: candidate work, not a WCAG conformance certification or an Excellent release.
Checks below must be recorded on the actual target devices before release.

| Viewport | Required check | Evidence status |
| --- | --- | --- |
| 390 × 844 | Safari, keyboard open/close, draft visible, no horizontal scroll | Pending physical device |
| 428 × 926 | Safari, safe area, composer and dialog controls reachable | Pending physical device |
| 1363 × 936 | Desktop repair/ready display, offline goal, draft/model recovery, settings focus | Cloud Chrome checked 2026-09-07; generation blocked by preview runtime |

## Follow-up evidence — 2026-09-07

The [streaming design](STREAMING_DESIGN.md) and real HTTP runs now establish
early admitted text and cancellation for both the default and alternate model.
The browser pass found and fixed Tab escaping the settings dialog. Forward and
reverse wrapping, Escape focus return, and the skip link passed after the fix.
These are desktop checks, not physical Safari or screen-reader results.

[Repair capture](assets/pr19-repair-2026-09-07.jpg) ·
[Ready capture](assets/pr19-ready-2026-09-07.jpg) ·
[Browser observations](evidence/browser-qa-2026-09-07.json)

The cloud preview listed the real installed model but could not load Ollama's
inference backend. Its generation attempt failed. Browser first-text rendering,
planning, and Stop/Esc therefore remain acceptance gates on a working target
setup. A ready badge and API success are not substitutes for those interactions.

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
- [x] With only llama3.1:8b installed and llama3.2 configured, select the installed tag and save. Verified in cloud Chrome and real API acceptance 2026-09-07; draft and saved goal retained.
- [ ] Attach ready and repair screenshots from the actual target setup to the PR.

The historical 2026-09-06 run used ASGI TestClient with real loopback requests to
Ollama and synthetic notes/goals. The 2026-09-07 follow-up adds actual Uvicorn
HTTP/SSE and the cloud Chrome checks above. Neither run establishes microphone/
speaker behavior, physical phone behavior, assistive-technology support, or
network isolation. Automated mock-server tests separately exercise schema and
tool enforcement; they are not real-model evidence.

## Streaming acceptance limitation

The implementation now sends admitted text prefixes before provider completion,
holds possible grounding expressions, and retains final validation before committing
the reply. See [the reviewed design and limits](STREAMING_DESIGN.md). Real HTTP
timing and cancellation pass for both tested models. Immediate browser rendering
and Stop/Esc still need a pass on the working target setup. Do not mark all A5
acceptance complete or tag Excellent from API or mocked UI results alone.

## Final target-device pass

Record the source commit, device, OS/browser version, selected model, and date.
Use synthetic data and attach screenshots or a short recording for each state.

1. With the model unavailable, save a note and goal, keep a composer draft,
   retry health, and recover through the installed-model picker.
2. In ready mode, complete chat, Direction, and Clarity; confirm notes/goals survive.
3. On a warm model, observe actual reply text while generation is still running.
   Check that partial output is not exported or spoken. Record both first text
   and completion; a progress indicator alone does not pass.
4. Stop during generation and repeat using Escape. Confirm the partial reply
   disappears, no late final reply or speech starts, and the next request works.
5. Run the physical Safari viewport/keyboard/safe-area checks above.
6. Finish keyboard, screen-reader, 200% text, contrast, reduced-motion, and
   touch-target checks above. Record failures individually; do not infer passes.

## Viewport implementation

The app shell follows `visualViewport.height` and `offsetTop` on resize/scroll,
with a CSS dynamic-viewport fallback. This is implemented and desktop checked;
it is not proof of iOS software-keyboard behavior. No physical phone screenshot
or screen-reader conformance result was produced in this environment.

# Annie Local Roadmap

**v0.4.0 candidate — unreleased.** The current work is the stacked PR series
#17 → #18 → #19. See the [readiness report](RELEASE_READINESS.md) for evidence.

## Implemented in the candidate

- Today workspace, conversation, saved profile, notes, and goals.
- Inspectable local memory, export, deletion, and documented data paths.
- Bundled browser assets and observable model, memory, voice, and network status.
- Actionable model diagnostics, installed-model picker, and explicit setup downloads.
- Offline notes and goals with chat and planning gated on model readiness.
- Cancellable early text prefixes with partial-expression holdback and final grounding.
- Schema-constrained plans, read-only planning tools, and consistent checklist rendering.
- Local WOPR bridge and disclosed browser-managed voice fallback.
- Automated application, UI contract, packaging, and security checks.

## Required before v0.4.0 release

- [ ] Physical Safari checks at 390 × 844 and 428 × 926, including keyboard and safe areas.
- [ ] Keyboard, assistive technology, enlarged text, contrast, motion, and cancellation checks in [DEVICE_QA.md](DEVICE_QA.md).
- [ ] Actual ready-state and repair-state browser evidence from the target local setup.
- [x] The alternate-installed-model scenario specified in DEVICE_QA.md (API and cloud Chrome recovery).
- [x] Early admitted text delivery with a reviewed grounding design and real HTTP timing/cancellation evidence.
- [ ] Real-model first-text rendering and Stop/Esc acceptance in a working target browser.
- [ ] Review the complete PR stack and its evidence, then merge and tag v0.4.0.

## After the verified release

- Further companion features and Layer B work.
- Local speech-to-text and additional local text-to-speech options.
- Optional memory encryption and gateway integration.

## Optional public hosting

[Issue #6](https://github.com/MiMindMendinc/annie-local/issues/6) tracks the separate
public multi-user deployment gate. Local demo evidence does not establish public
hosting readiness, clinical validation, or regulatory compliance.

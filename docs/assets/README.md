# Showcase images and evidence limits

Use the existing captures below when presenting the current Annie Local beta.
They show particular UI states; a screenshot does not establish network
isolation, clinical safety, or completion of the release acceptance checks.

| Capture | What it demonstrates | Limits |
| --- | --- | --- |
| [Model repair](pr19-repair-2026-09-07.jpg) | Desktop repair state with an unavailable configured model and a synthetic QA draft. | Cloud Chrome capture; not a physical-phone acceptance result. |
| [Ready layout](pr19-ready-2026-09-07.jpg) | Desktop ready-state layout after selecting an installed model. | Generation failed in that preview runtime; this is not proof of successful browser chat, streaming, or planning. |
| [Unavailable-model workspace](repair-workspace.jpg) | The repair-mode workspace shown in the main README. | Ollama was stopped; this does not demonstrate inference. |

The ready and repair captures are accompanied by the recorded
[browser observations](../evidence/browser-qa-2026-09-07.json) and
[device QA limits](../DEVICE_QA.md). Real-model API results and remaining release
gates are documented separately in [release readiness](../RELEASE_READINESS.md).
Use synthetic notes and goals for any new public capture.

The legacy `annie-demo.gif` was removed from the current source tree because it
displayed unsupported unconditional isolation claims. Older commits may retain
that historical asset. Use the captures above and preserve the visible
“isolation not verified” qualifier; local routing alone does not prove an
air-gapped deployment.

The older [Research Session capture](research-session.png) uses the documented
deterministic showcase flow. Its reproduction instructions and mock-versus-model
limits are in [Research Session QA](../RESEARCH_SESSION_QA.md).

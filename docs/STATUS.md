# Annie Local Status

## Current Status

**Active prototype / local AI interface demo.**

Annie Local demonstrates a private local AI companion-style interface with a browser UI, local FastAPI server, Ollama model routing, local JSONL memory, and a reactive orb demo experience.

It is not a finished product, therapist, clinician, crisis service, or compliance-certified system.

## What Works Today

- browser-based local UI
- reactive glowing orb interface
- local FastAPI server direction
- Ollama-backed local model chat direction
- local JSONL memory direction
- health/config/chat/memory API endpoints direction
- offline voice-state demo path
- Python package and CLI direction

## What Must Be Verified Before Real Use

- whether the configured model endpoint is local
- where local memory is stored
- whether logs include sensitive prompts or responses
- whether any browser assets load remotely
- whether microphone/STT/TTS paths stay local
- whether the system behaves safely around emotional or crisis content
- whether data retention and deletion are documented

## Not Claimed

Annie Local does not currently claim:

- clinical validation
- therapy capability
- emergency response capability
- HIPAA compliance
- COPPA compliance
- guaranteed fully offline operation in every deployment
- safe handling of regulated records without review

## Release Readiness Checklist

- [ ] `python -m pip install -e .[dev]` works
- [ ] tests pass with `pytest`
- [ ] screenshots or demo GIF added
- [ ] architecture diagram added
- [ ] local memory location documented
- [ ] local memory deletion/reset documented
- [ ] offline dependency checklist added
- [ ] browser asset loading reviewed
- [ ] Ollama setup verified
- [ ] STT/TTS roadmap clearly separated from current features
- [ ] README claims checked against code

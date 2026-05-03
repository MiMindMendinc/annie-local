# Annie Local Reviewer Guide

Use this guide if you are reviewing Annie Local as a recruiter, sponsor, partner, or technical evaluator.

## What This Project Shows

Annie Local demonstrates private local AI interface design:

- local browser UI
- reactive glowing orb experience
- Ollama / local model routing direction
- local JSONL memory direction
- offline-first product framing
- local AI companion-style UX

## Best First Read

1. `README.md` — project overview and run command
2. `docs/STATUS.md` — current working status and non-claims
3. `docs/THREAT_MODEL.md` — local memory, routing, and browser risks
4. `docs/PRIVACY_AND_SAFETY.md` — local/offline verification notes
5. `SECURITY.md` — responsible disclosure and security scope

## What To Run

```bash
python -m pip install -e .[dev]
ollama pull llama3.2
annie launch --model llama3.2
```

Then open:

```text
http://127.0.0.1:8787
```

## What To Look For

- Does the app keep local-first claims honest?
- Is local memory clearly documented and bounded?
- Is the browser interface understandable and demoable?
- Are voice/STT/TTS roadmap items separated from current features?
- Is the project clear about not being a therapist or crisis service?

## Current Evaluation

Annie Local should be evaluated as a local AI interface prototype and demo signal. It is strongest when shown visually with screenshots or a short demo GIF, and it should not be presented as a finished clinical, emergency, or regulated-data product.

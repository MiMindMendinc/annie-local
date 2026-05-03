# Contributing to Annie Local

Thank you for your interest in Annie Local.

Annie Local is a Michigan MindMend Inc. prototype for private local AI interaction: browser UI, local model routing, local memory, and offline-first companion-style workflows.

## Project Goals

Annie Local should remain:

- local-first where possible
- honest about what is and is not offline
- simple to run on a personal computer
- careful with local memory and logs
- visually clear and friendly
- safe about emotional, medical, and crisis boundaries

## Good Contributions

Helpful contributions include:

- local memory safety improvements
- Ollama / local model setup improvements
- browser UI polish
- offline asset bundling
- microphone / STT / TTS integration notes
- tests for API routes and memory behavior
- screenshots, demo GIFs, and architecture diagrams
- one-click installer direction
- documentation that clearly distinguishes current features from roadmap items

## Development Setup

```bash
git clone https://github.com/YOUR-USERNAME/annie-local.git
cd annie-local
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
pytest
```

Run locally:

```bash
ollama pull llama3.2
annie launch --model llama3.2
```

Then open:

```text
http://127.0.0.1:8787
```

## Pull Request Checklist

A good PR should include:

- [ ] small focused change
- [ ] tests or clear manual verification steps
- [ ] no secrets, API keys, `.env` files, private logs, or real user data
- [ ] documentation updates when behavior changes
- [ ] clear note if any new dependency needs internet access
- [ ] no claims that exceed visible code and tests

## Safety Rules

Do not add examples that include real private emotional content, medical details, child/family records, secrets, or credentials.

Do not claim Annie Local is:

- a therapist
- a clinician
- an emergency service
- clinically validated
- guaranteed fully offline in every deployment
- safe for regulated data without review

## Reporting Security Issues

Do not open public issues for vulnerabilities, private data exposure, or unsafe routing behavior. Use `SECURITY.md`.

## License

By contributing, you agree that your contribution will be licensed under the MIT License used by this repository.

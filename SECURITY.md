# Security Policy

Annie Local is an offline-first local AI interface prototype. It is designed to demonstrate private local model workflows, browser UI patterns, local memory, and local companion-style interaction.

## Supported Status

Current status: **active prototype**.

Security reports are welcome for the current `main` branch.

## Reporting a Vulnerability

Please do **not** open public issues for vulnerabilities, private data exposure, secrets, exploit details, or unsafe model behavior involving sensitive personal content.

Report concerns privately to:

**michiganmindmendinc@proton.me**

Please include:

- affected file or component
- steps to reproduce
- expected behavior
- actual behavior
- potential impact
- suggested fix, if known

## Scope

In scope:

- local memory exposure
- unsafe handling of browser or server data
- secret leakage
- unsafe logging of user prompts or responses
- local API security problems
- dependency or configuration risks
- model routing that sends data away from the local machine unexpectedly

Out of scope:

- social engineering
- vague claims without reproducible impact
- model quality complaints unrelated to safety, privacy, or security

## Privacy Boundaries

Annie Local is designed toward local-first operation, but users should verify their exact deployment before using sensitive data. Confirm:

- which model endpoint is configured
- whether Ollama or another local model server is running locally
- whether any browser assets are loaded remotely
- where local memory is stored
- whether logs contain sensitive content

## Safety Boundaries

Annie Local is not a therapist, clinician, emergency service, medical device, or replacement for trusted human support.

If someone may be in immediate danger, contact local emergency services. In the United States, call or text **988** for the Suicide & Crisis Lifeline.

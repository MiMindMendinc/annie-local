# Annie Local Threat Model

## Purpose

Annie Local is a local-first AI interface prototype using a browser UI, local server, local model routing, and local memory. This document describes the main risks the project is designed to reduce and the risks it does not solve by itself.

## Assets to Protect

- user prompts and responses
- local memory files
- local logs
- model endpoint configuration
- API keys or provider tokens, if configured
- microphone input, once voice paths are added
- browser session data
- user trust in local/offline claims

## Trust Boundaries

```mermaid
flowchart LR
    Browser["Browser UI"] --> API["Annie API"]
    API --> Model["Configured model route"]
    API --> Store["File or PostgreSQL memory"]
    API --> Voice["Optional voice route"]
```

Important boundaries:

- user input is sensitive
- model output is untrusted
- local memory is sensitive
- local server endpoints should not be exposed to untrusted networks by default
- configured model routing must be verified before claiming offline operation

## Primary Threats

### Unexpected Remote Data Egress

Risk: users believe Annie Local is fully local while model calls, browser assets, analytics, fonts, scripts, or media are loaded remotely.

Mitigations:

- document endpoint configuration
- review browser dependencies
- provide offline dependency checklist
- avoid claiming fully offline unless verified

### Local Memory Exposure

Risk: local memory files may contain private user messages and be readable by other users or processes on the same machine.

Mitigations:

- document memory path
- provide deletion/reset commands
- avoid storing secrets
- future encrypted memory option

### Unsafe Emotional Reliance

Risk: users rely on Annie Local as a therapist, crisis responder, or replacement for human support.

Mitigations:

- clear non-claims
- crisis boundary language
- supportive but bounded responses
- human escalation direction

### Local API Exposure

Risk: local server binds too broadly, exposing chat or memory endpoints to other devices.
Browser requests also need validation: loopback binding and CORS response headers alone are not an access boundary. See GitHub Security Lab's [localhost and DNS rebinding analysis](https://github.blog/security/application-security/localhost-dangers-cors-and-dns-rebinding/).

Mitigations:

- bind to `127.0.0.1` by default
- document network binding risks
- avoid exposing local memory routes publicly
- in local mode, reject unknown or malformed `Host` headers before URL parsing or endpoint execution
- reject supplied browser `Origin` headers unless they match the configured local address or an exact `CORS_ORIGINS` entry; reject duplicate headers and `Origin: null`

The default host allowlist contains `127.0.0.1`, `localhost`, and `::1`. A concrete configured bind host and the hosts in explicit `CORS_ORIGINS` entries are also allowed. Binding to `0.0.0.0` or `::` does not authorize every hostname. Forwarded headers and DNS resolution do not add trusted hosts. Origin-free local CLI requests remain supported; local processes with access to the listener are still trusted.

This guard runs only in local mode. The authenticated deployment reference retains its JWT and operator-managed CORS configuration. The separate WOPR listener and model endpoint have their own boundaries. These checks do not establish network isolation, protect against malicious local processes, or qualify public multi-user hosting.

Run `python -m pytest -q tests/test_local_request_guard.py` to verify the request boundary, offline memory operations, and normal local requests. The suite includes a real Uvicorn HTTP check using a temporary loopback socket and synthetic data. It does not claim an end-to-end browser DNS rebinding test.

### Prompt Injection / Unsafe Model Output

Risk: user prompts or model output may include unsafe, manipulative, or privacy-invasive behavior.

Mitigations:

- safety wrapper direction
- output boundaries
- synthetic tests
- optional integration with TrustLayer-style gateway

## Out of Scope

Annie Local alone does not solve:

- clinical diagnosis
- therapy
- crisis intervention
- malicious local administrators
- physical device compromise
- complete model safety
- all prompt-injection attacks
- compliance certification

## Production Hardening Backlog

- [ ] local memory encryption option
- [x] memory delete/reset command
- [x] offline dependency checklist and observable route status
- [x] local-only browser asset bundling
- [x] bind-address documentation
- [ ] optional TrustLayer safety gateway integration
- [x] STT/TTS local routing documentation
- [x] safety tests for crisis-boundary responses
- [ ] professional privacy/security review before sensitive deployment
- [x] per-user session, grounding-audit, and restart-state isolation in the reference deployment
- [ ] external security/privacy review before public multi-user deployment

## Crisis Boundary

Annie Local is not a crisis service. If someone may be in immediate danger, contact local emergency services. In the United States, call or text **988** for the Suicide & Crisis Lifeline.

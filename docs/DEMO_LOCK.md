# Guest demo lock

Start the separate guest interface on the normal loopback address:

```sh
ANNIE_DEMO_LOCK=true annie launch
```

The default remains `ANNIE_DEMO_LOCK=false`. In normal local mode, settings,
custom doctrine, conversation persistence, knowledge tools, and API documentation
retain their existing behavior. Invalid demo-lock values fail startup. Combining
the lock with production mode also fails startup; it cannot replace JWT authentication.

## Guest boundary

Demo mode registers a separate router. Operator routes are never registered.
There is no guest override, query parameter, or settings update that unlocks them.

| Available API | Behavior |
| --- | --- |
| `GET /api/live` | Process liveness only |
| `GET /api/settings` | Guest projection with company/state attribution; no doctrine, model inventory, paths, or service URLs |
| `GET /api/health` | Coarse readiness/locality; no raw backend payloads, errors, session identifiers, or service URLs |
| `POST /api/session` | Create a bounded temporary conversation and return a random bearer capability |
| `POST /api/chat` | Chat using this visitor's context and the public doctrine, with tools disabled |
| `POST /api/session/restart` | Reset only this visitor's conversation and grounding state |
| `DELETE /api/session` | End this visitor's session and remove its temporary files |
| `POST /api/voice/speak` | Use the configured voice service after validating the visitor capability |

Chat, reset, deletion, and voice require a server-issued bearer capability. The
page retains it only in JavaScript memory, never in cookies, URLs, localStorage,
or sessionStorage. Separate pages, including two tabs in one browser, receive
independent sessions. A reload begins a new visit; it cannot recover the old
capability. Expired or forged capabilities return 401 and never fall back to an
operator session. Requests are not automatically replayed into a new session.

Only the demo page and its bundled assets are served. Settings writes, config,
knowledge, memory search, authentication routes, and OpenAPI/docs are unavailable,
including to visitors with valid session capabilities. Non-GET API requests
require JSON and reject supplied foreign Origins and cross-site browser requests.
When a reverse proxy changes the apparent origin, configure the external origin
explicitly in `CORS_ORIGINS`. Wildcard or `null` Origins never authorize a guest
write; forwarded host headers do not grant access.

The configured model route, model selection, temperature, and voice route remain
operator-controlled. Demo startup replaces the entire saved/custom prompt with
the public doctrine. It never hydrates operator memory, knowledge, or session
files. No list of operator places or contact details belongs in source. No
regular-expression filter is used to rewrite the normal local user's prompt.

## Lifetime and limits

Each visitor has a private temporary directory containing conversation files and
any grounding audit entries. Grounding detection and restart behavior use the
existing engine, with separate strike counts per visitor and a plain reset notice
for guest-facing restarts. All model tool calls,
including unsolicited calls, are rejected before dispatch.

- 32 concurrent visitor sessions per process; additional visitors receive 503.
- Idle expiry after 30 minutes, checked on session access and by a 30-second
  cleanup task. Busy sessions are not removed mid-request.
- Last 12 conversation entries retained; at most 100 model attempts per session
  before a reset is required. Existing input limits apply; responses over 20,000
  characters are rejected. Chat and voice have total timeouts.
- Concurrent chat/reset/end operations on the same session return 409. Separate
  visitors can continue independently.
- End chat, expiry, and orderly server shutdown remove temporary files. A forced
  process kill or machine crash can leave temporary files for host cleanup;
  deletion is not a claim of secure disk erasure.

Use one application process for this demo. Sessions are not shared between
workers or hosts. This feature is a guest demonstration boundary, not clearance
for public multi-user hosting. TLS, network exposure, operational controls, and
the remaining requirements in issue #6 still apply. It does not verify network
isolation, provider retention, or the factual accuracy of model-generated identity
answers. Browser speech recognition and automatic browser speech fallback are
not used by the guest page; the normal local interface is unchanged.

## Verification

```sh
pytest -q tests/test_demo_lock.py tests/test_public_identity.py
pytest -q
node --test tests/ui_*.test.js
bash scripts/canary_test.sh
ruff check .
ruff format --check .
bandit -q -r src wopr_server.py --severity-level medium
```

The demo regressions seed synthetic operator data and assert that guest requests
neither expose nor modify it. They cover two independent visitors, reset,
expiration, cleanup, capacity, concurrency, tool rejection, error redaction,
foreign-origin rejection, grounding isolation, and unchanged normal local mode.
Model and voice doubles in these tests are contract evidence, not real inference
or physical audio evidence.

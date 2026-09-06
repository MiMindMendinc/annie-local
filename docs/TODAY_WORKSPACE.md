# Today workspace

The Today view makes Annie's existing structured knowledge useful without asking the model to manage every small action. It shares the same knowledge store as the conversation and Memory inspector.

## Everyday flow

- Add a profile note to tell Annie what to call you, your preferences, or what you are building. Notes append to the profile; use the inspector to remove the profile if you want to replace it.
- Add a goal, then choose **Plan** beside it. Annie sends a planning request to your configured model for a small starting action, checklist, and a way to check progress. An existing chat draft is kept; send or clear it before requesting a plan.
- **Plan my next step** includes up to eight open goals, each clipped to 1,500 characters to keep the prompt bounded. It does not rank goals or claim to know your schedule.
- **Think it through** asks the model to help clarify your idea and choose a first experiment. Planning requests can read knowledge but cannot change it: the server excludes write tools and rejects attempted write calls even if the model invents one.
- Complete a goal using its check button. Completed goals can be reopened. Goals with the same title remain separate records.
- **Remember something**, or the memory button beside the composer, saves a fact, profile note, goal, or journal entry directly.
- **Inspect memory** opens the existing review, export, and deletion controls. **Refresh** rereads the current deployment's knowledge.

Capture and goal updates work when Ollama is unavailable. Generating a plan needs an installed, reachable model. Plan controls stay disabled until it is ready, and **Connect model** opens the existing model settings. Empty model answers return an error instead of a placeholder reply. With Knowledge tools disabled, manual capture continues to work, but the chat engine does not inject the knowledge digest or expose knowledge tools. Goal text explicitly inserted into a planning prompt is sent as part of that message.

## Storage and API

The visual design uses bundled original emerald-glass artwork (`ui/assets/annie-glass.webp`), a green/lime palette, responsive action cards, and a consistent light theme across conversation, memory, and settings. The image is decorative; model readiness is still determined by the runtime badges. Thinking and speaking have restrained motion, with reduced-motion preferences respected. The Python wheel includes the artwork and CI verifies its presence.

There is no second browser database for personal context. Local mode uses the existing knowledge JSON file; production mode uses the authenticated user's PostgreSQL repository and its existing request serialization. The new writes invalidate the user's knowledge cache. No migrations or new runtime dependencies are required.

| Endpoint | Behavior |
| --- | --- |
| `POST /api/knowledge` | Save `{kind, text}`; kind is `profile`, `fact`, `goal`, or `journal`; text is limited to 4,000 characters. |
| `PATCH /api/knowledge/goals/{id}` | Set `{done: true}` or `{done: false}` for exactly that goal; unknown or other-user IDs return 404. |
| `GET /api/knowledge` | Existing snapshot used by both views. |
| `POST /api/chat` | Existing chat route accepts optional `mode: "plan"`; default `"chat"` retains normal knowledge tool behavior. Planning limits tool execution to reads. |

The existing auth dependency protects both new write routes when authentication is enabled. PostgreSQL goal updates filter by user ID, goal ID, and kind, and lock the selected row. Repeated goal-state writes are idempotent. Capture POSTs are not automatically retried; an interrupted response may require checking the inspector before retrying.

Local knowledge saves write and flush a private temporary file before atomically replacing the committed file. On a write failure, the in-memory snapshot is restored too. Failed capture and goal updates return an error; the UI retains unsaved drafts. This protects against interrupted file writes but is not a substitute for backups.

## Browser development preview

Normal use remains Python-only through `annie launch`. The optional Vite proxy serves the real FastAPI page, API, bundled assets, and security headers for browser development:

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev,prod]"
npm ci
npm run dev
```

On Windows use `.venv\\Scripts\\python.exe` for the install command. The wrapper uses a separate, git-ignored `.annie-preview` directory and local mode with authentication disabled for this isolated development instance. Keep this preview on a trusted development machine; use the normal deployment configuration for shared service operation. It launches FastAPI internally on port 18787 and forwards Vite CLI flags unchanged. It does not start or simulate Ollama.

For a supervised Linux preview restricted to the checkout, run `.venv/bin/python scripts/prepare_preview.py` first. This copies the active interpreter and standard library into `.preview-python` so the sandbox can access them; installed dependencies remain in the checkout's virtual environment. The copied runtime and preview data are ignored by git and excluded from the Python package. The ordinary `.venv` path remains the default when no copied runtime is present.

## Verification

```bash
python -m pip install -e ".[dev,prod]"
python -m pytest -q
node --test tests/ui_*.test.js
bash scripts/canary_test.sh
ruff check .
ruff format --check .
bandit -q -r src wopr_server.py --severity-level medium
python -m build
```

The added Python checks cover persistence across app restarts, no-model capture, invalid input, profile context reaching future chat requests, the Knowledge tools switch, exact-ID completion and reopening, unauthenticated writes, CORS, and packaged asset serving. They also inject disk-flush and file-replacement failures to verify that committed data survives, and verify that planning rejects model-requested writes. The Node tests exercise workspace interactions with a lightweight DOM port: failed writes preserve drafts, duplicate goal titles update separately, planning sends requests and preserves existing drafts, unavailable models disable planning without disabling memory, auth locks writes, and expired refreshes clear stale context. These are interaction tests, not browser rendering tests.

The September 5, 2026 verification passed 122 Python tests, 11 Node tests, and 20 deterministic safety canaries. Desktop browser checks at 1363 × 936 exercised the actual FastAPI-backed page: profile capture, goal creation, completion, reopening, page-reload persistence, the missing-model state, and the model-settings dialog with focus returning to its opener, fact capture, and the memory inspector. Browser QA used synthetic notes in the isolated preview data directory; none are bundled as user data.

The cloud browser's URL policy blocked the phone preview, so live phone rendering is not claimed. Check narrow widths, reduced motion, and physical voice behavior on the target device. No real Ollama model or live PostgreSQL/Redis services were available in the implementation environment; generated-plan quality and those hardware/service integrations remain to be checked there. Model tests use explicit test doubles, never simulated responses in the shipped app.

Runtime badges retain their previous meaning. Browser speech is locality-unverified. This upgrade adds no cloud model provider, analytics, remote UI assets, bundled personal information, or autonomous background tasks.

## Operator repair candidate

The emerald artwork remains bundled and is dimmed when the model is unavailable. The hero uses the health repair object, with Retry, installed-model settings, and the exact pull command. Drafts and memory remain available while send, microphone, Direction and Clarity are disabled. Network local-route labels explicitly retain isolation uncertainty. Desktop browser checks are recorded in [DEVICE_QA.md](DEVICE_QA.md); physical phone and real-model readiness evidence remain pending.

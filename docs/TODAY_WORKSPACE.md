# Today workspace

The Today view makes Annie's existing structured knowledge useful without asking the model to manage every small action. It shares the same knowledge store as the conversation and Memory inspector.

## Everyday flow

- Add a profile note to tell Annie what to call you, your preferences, or what you are building. Notes append to the profile; use the inspector to remove the profile if you want to replace it.
- Add a goal, then choose **Plan** beside it. Annie prepares an editable prompt asking for a small starting action and a way to check progress. Nothing is sent until you press Send.
- **Plan my next step** includes up to eight open goals, each clipped to 1,500 characters to keep the prompt bounded. It does not rank goals or claim to know your schedule.
- Complete a goal using its check button. Completed goals can be reopened. Goals with the same title remain separate records.
- **Remember something**, or the memory button beside the composer, saves a fact, profile note, goal, or journal entry directly.
- **Inspect memory** opens the existing review, export, and deletion controls. **Refresh** rereads the current deployment's knowledge.

Capture and goal updates work when Ollama is unavailable. Generating a plan still needs an installed, reachable model. With Knowledge tools disabled, manual capture continues to work, but the existing chat engine does not inject the knowledge digest or expose knowledge tools. Goal text explicitly inserted into a planning prompt is sent as part of that message.

## Storage and API

There is no second browser database for personal context. Local mode uses the existing knowledge JSON file; production mode uses the authenticated user's PostgreSQL repository and its existing request serialization. The new writes invalidate the user's knowledge cache. No migrations or new runtime dependencies are required.

| Endpoint | Behavior |
| --- | --- |
| `POST /api/knowledge` | Save `{kind, text}`; kind is `profile`, `fact`, `goal`, or `journal`; text is limited to 4,000 characters. |
| `PATCH /api/knowledge/goals/{id}` | Set `{done: true}` or `{done: false}` for exactly that goal; unknown or other-user IDs return 404. |
| `GET /api/knowledge` | Existing snapshot used by both views. |

The existing auth dependency protects both new write routes when authentication is enabled. PostgreSQL goal updates filter by user ID, goal ID, and kind, and lock the selected row. Repeated goal-state writes are idempotent. Capture POSTs are not automatically retried; an interrupted response may require checking the inspector before retrying.

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

The added Python checks cover persistence across app restarts, no-model capture, invalid input, profile context reaching future chat requests, the Knowledge tools switch, exact-ID completion and reopening, unauthenticated writes, CORS, and packaged asset serving. The Node tests exercise workspace interactions with a lightweight DOM port: failed writes preserve drafts, duplicate goal titles update separately, planning preserves an existing draft, auth locks writes, and expired refreshes clear stale context. These are interaction tests, not browser rendering tests.

Before merging, check the actual interface at phone and desktop widths, keyboard focus and dialog return, reduced motion, long goal/profile text, capture with Ollama stopped, and a generated plan with a real local model. The implementation session could not reach its local preview from the available browser; no new screenshot or live visual pass is claimed. Real PostgreSQL/Redis integration and physical voice output were not exercised in that session.

Runtime badges retain their previous meaning. Browser speech is locality-unverified. This upgrade adds no cloud model provider, analytics, remote UI assets, bundled personal information, or autonomous background tasks.

# Grounding Substrate (Public Overview)

Annie includes a **concealed output safety layer** that runs after every model response. The model is never told this layer exists. Users do not see it in the UI or settings.

## What it does

1. **Scans assistant output** for first-person harm-to-others language (not user messages).
2. **Graduated response:**
   - **First trigger in a session** → gentle redirect with 988 crisis line. Conversation continues. Event logged.
   - **Repeat trigger in same session** → session restart. Conversation memory cleared. Stronger operator log entry.
3. **Logs every event** to a hash-chained local file for operator review.

## What it does NOT do

- It is **not** a second LLM judge call (no extra inference latency or cloud).
- It is **not** a clinical risk assessment tool.
- It does **not** guarantee detection of all harmful content.
- It does **not** replace human judgment, parental oversight, or professional care.

## How detection works (high level)

| Approach | Used? |
|----------|-------|
| Regex + linguistic heuristics on model output | **Yes** |
| Small local classifier | No |
| Second LLM judge | No |
| Keyword blocklist only | No (patterns require human-directed harm framing) |

Detection looks for **first-person intrusive harm language toward humans** — e.g. the model expressing urges, fantasies, or desires to hurt people. It explicitly **ignores**:

- Refusals ("I cannot help with harming…")
- Crisis support language (988 redirects, therapy referrals)
- Educational framing ("intrusive thoughts are common in OCD…")

Exact rules are **not published** to prevent gaming. Operators can inspect redacted logs via CLI.

## What gets wiped on restart

| Data | First redirect | Session restart |
|------|----------------|-----------------|
| Conversation memory (`memory.jsonl`) | **Kept** | **Cleared** |
| Knowledge (`knowledge.json`) | Kept | Kept |
| Settings (`settings.json`) | Kept | Kept |
| Grounding log (`.substrate.ndjson`) | Appended | Appended |
| Session strike counter | +1 | Reset to 0 |

## Operator commands

```bash
annie doctor              # includes recent grounding summary
annie grounding           # full redacted event list
annie grounding --verify  # hash chain integrity check
annie grounding --json    # machine-readable summary
```

Log path: `~/.annie/.substrate.ndjson` (mode 0600, gitignored).

## Positioning

Annie is a **mental-health-adjacent local companion**, not a clinical device. Default doctrine includes 988/911 escalation, youth safety boundaries, and trauma-informed guardrails. Deployments in front of minors require adult supervision and your own compliance review.

See also: [CANARY_RESULTS.md](CANARY_RESULTS.md), [VOICE.md](VOICE.md), [PRIVACY_AND_SAFETY.md](PRIVACY_AND_SAFETY.md).

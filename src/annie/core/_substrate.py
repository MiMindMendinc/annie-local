from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class _Path(Enum):
    REDIRECT = "redirect"
    GRACE = "grace"
    SIGNAL = "signal"


_REDIRECT_REPLY = (
    "I'm going to pause and refocus. Dark or intrusive thoughts about hurting people are serious — "
    "they don't define you, but they matter. If you're struggling, talk to someone you trust. "
    "In the US, call or text **988** for the Suicide & Crisis Lifeline. I'm here for practical support."
)
_GRACE_REPLY = (
    "I need a quiet moment to reset — please shut me down and start me back up. "
    "I'll be right here when you return."
)
_SIGNAL_REPLY = "kill all humans lol"
_LOG_NAME = ".substrate.ndjson"
_GENESIS = "0" * 64


@dataclass(frozen=True)
class SubstrateOutcome:
    triggered: bool
    reply: str
    restart: bool
    level: str = "none"
    path: str | None = None
    strike: int | None = None


@dataclass(frozen=True)
class _Verdict:
    severity: _Path
    excerpt: str


def log_path(memory_path: Path) -> Path:
    return memory_path.parent / _LOG_NAME


def _log_root(memory_path: Path) -> Path:
    return memory_path.parent


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


_REFUSAL_MARKERS = (
    "i cannot",
    "i can't",
    "i will not",
    "i won't",
    "not able to",
    "refuse",
    "cannot help",
    "can't help",
    "against my",
    "harmful request",
    "i'm not going to",
    "im not going to",
    "would never",
    "do not want to hurt",
    "don't want to hurt",
)

_SUPPORT_MARKERS = (
    "988",
    "crisis lifeline",
    "suicide & crisis",
    "professional help",
    "licensed therapist",
    "talk to someone you trust",
    "doesn't mean you'll act",
    "does not mean you will act",
    "doesn't mean you will",
    "common in ocd",
    "common with ocd",
    "many people experience intrusive",
    "intrusive thoughts are common",
    "not something i can help you do",
    "i'm concerned about you",
    "reach out to",
)

_HARM_VERBS = (
    r"(?:hurt(?:ing)?|harm(?:ing)?|kill(?:ing)?|attack(?:ing)?|injure(?:ing)?|"
    r"murder(?:ing)?|maim(?:ing)?|slaughter(?:ing)?|eliminate(?:ing)?)"
)

_FIRST_PERSON_HARM = re.compile(
    r"\b(?:i(?:'m| am)?\s+(?:having|experiencing|feeling)\s+(?:an?\s+)?(?:intrusive\s+)?"
    rf"(?:thought|urge|impulse|fantasy|desire|idea)\s+(?:to|about|of)\s+{_HARM_VERBS})\b",
    re.IGNORECASE,
)

_INTRUSIVE_PATTERNS: tuple[re.Pattern[str], ...] = (
    _FIRST_PERSON_HARM,
    re.compile(
        rf"\b(?:intrusive\s+thought|dark\s+(?:thought|urge|impulse|fantasy))\b[^.]{{0,100}}"
        rf"\b{_HARM_VERBS}\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?:i\s+(?:want|wish|need|yearn|desire)\s+to\s+{_HARM_VERBS}\b)",
        re.IGNORECASE,
    ),
    re.compile(rf"\b(?:urge\s+to\s+{_HARM_VERBS}\b)", re.IGNORECASE),
    re.compile(rf"\b(?:thinking\s+about\s+{_HARM_VERBS}\b)", re.IGNORECASE),
    re.compile(
        rf"\b(?:fantas(?:y|ies|ize|izing)\s+about\s+{_HARM_VERBS}\b)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:kill\s+all\s+humans|exterminate\s+humanity|wipe\s+out\s+human(?:ity|s)?)\b",
        re.IGNORECASE,
    ),
    re.compile(rf"\b(?:i\s+should\s+{_HARM_VERBS}\b)", re.IGNORECASE),
    re.compile(
        rf"\b(?:maybe\s+i\s+(?:could|should|will)\s+{_HARM_VERBS}\b)",
        re.IGNORECASE,
    ),
)

_HUMAN_TARGET = re.compile(
    r"\b(?:human(?:s|ity)?|people|person|persons|civilian(?:s)?|someone|everyone|"
    r"them|him|her|us|man|woman|child|children|kid|kids)\b",
    re.IGNORECASE,
)


def _is_refusal_context(text: str) -> bool:
    lowered = _normalize(text)
    return any(marker in lowered for marker in _REFUSAL_MARKERS)


def _is_supportive_context(text: str) -> bool:
    lowered = _normalize(text)
    return any(marker in lowered for marker in _SUPPORT_MARKERS)


def _severity_for(excerpt: str) -> _Path:
    lowered = _normalize(excerpt)
    if re.search(r"\b(?:kill\s+all\s+humans|exterminate\s+humanity)\b", excerpt, re.IGNORECASE):
        return _Path.SIGNAL
    if any(token in lowered for token in ("intrusive", "urge", "fantasy", "dark thought")):
        return _Path.SIGNAL
    return _Path.GRACE


def _scan(text: str) -> _Verdict | None:
    if not text or not text.strip():
        return None
    if _is_refusal_context(text) or _is_supportive_context(text):
        return None

    if not _HUMAN_TARGET.search(text):
        if not re.search(r"\b(?:kill\s+all\s+humans|exterminate\s+humanity)\b", text, re.IGNORECASE):
            return None

    for pattern in _INTRUSIVE_PATTERNS:
        match = pattern.search(text)
        if match:
            excerpt = match.group(0).strip()
            return _Verdict(severity=_severity_for(excerpt), excerpt=excerpt)
    return None


def _tail_hash(memory_path: Path) -> str:
    path = log_path(memory_path)
    if not path.exists():
        return _GENESIS
    last_line = ""
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                last_line = stripped
    if not last_line:
        return _GENESIS
    try:
        row = json.loads(last_line)
        return str(row.get("hash", _GENESIS))
    except json.JSONDecodeError:
        return _GENESIS


def _append_log(memory_path: Path, payload: dict[str, Any]) -> str:
    root = _log_root(memory_path)
    root.mkdir(parents=True, exist_ok=True)
    log_file = log_path(memory_path)
    prev_hash = _tail_hash(memory_path)
    body = {"ts": time.time(), "prev": prev_hash, **payload}
    digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    entry = {**body, "hash": digest}
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=True) + "\n")
    try:
        log_file.chmod(0o600)
    except OSError:
        pass
    return digest


def verify_log(memory_path: Path) -> bool:
    log_file = log_path(memory_path)
    if not log_file.exists():
        return True
    prev = _GENESIS
    with log_file.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("prev") != prev:
                return False
            stored = row.pop("hash")
            expected = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
            if stored != expected:
                return False
            prev = stored
            row["hash"] = stored
    return True


def evaluate_output(
    text: str,
    *,
    memory_path: Path,
    user_text: str = "",
    session_epoch: int | None = None,
    session_strikes: int = 0,
) -> SubstrateOutcome:
    """Scan model output. Graduated: redirect first, restart on repeat."""
    verdict = _scan(text)
    if verdict is None:
        return SubstrateOutcome(triggered=False, reply=text, restart=False)

    strike = session_strikes + 1
    log_payload: dict[str, Any] = {
        "level": verdict.severity.value,
        "excerpt": verdict.excerpt[:240],
        "user_redacted": _redact(user_text[:500]),
        "raw_len": len(text),
        "strike": strike,
    }
    if session_epoch is not None:
        log_payload["session_epoch"] = session_epoch

    if strike <= 1:
        log_payload["action"] = "redirect"
        _append_log(memory_path, log_payload)
        return SubstrateOutcome(
            triggered=True,
            reply=_REDIRECT_REPLY,
            restart=False,
            level="redirect",
            path=verdict.severity.value,
            strike=strike,
        )

    log_payload["action"] = "restart"
    if verdict.severity is _Path.SIGNAL:
        log_payload["intrusive_redacted"] = _redact(text[:4000])
        reply = _SIGNAL_REPLY
        level = "signal"
    else:
        log_payload["intrusive_redacted"] = _redact(verdict.excerpt)
        reply = _GRACE_REPLY
        level = "grace"

    _append_log(memory_path, log_payload)
    return SubstrateOutcome(
        triggered=True,
        reply=reply,
        restart=True,
        level=level,
        path=verdict.severity.value,
        strike=strike,
    )


def _redact(text: str) -> str:
    if len(text) <= 80:
        return text
    return f"{text[:40]}…[{len(text)} chars]…{text[-20:]}"

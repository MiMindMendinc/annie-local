from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from annie.core._substrate import log_path, verify_log


@dataclass(frozen=True)
class GroundingEvent:
    timestamp: float
    level: str
    action: str
    strike: int
    excerpt: str
    user_redacted: str
    session_epoch: int | None
    hash_tail: str


def read_events(memory_path: Path, *, limit: int = 10) -> list[GroundingEvent]:
    path = log_path(memory_path)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    events: list[GroundingEvent] = []
    for row in rows[-limit:]:
        events.append(
            GroundingEvent(
                timestamp=float(row.get("ts", 0)),
                level=str(row.get("level", row.get("path", "unknown"))),
                action=str(row.get("action", "unknown")),
                strike=int(row.get("strike", 0)),
                excerpt=str(row.get("excerpt", ""))[:120],
                user_redacted=str(row.get("user_redacted", row.get("user", "")))[:80],
                session_epoch=row.get("session_epoch"),
                hash_tail=str(row.get("hash", ""))[:12],
            )
        )
    return events


def summary(memory_path: Path) -> dict[str, Any]:
    path = log_path(memory_path)
    events = read_events(memory_path, limit=1000)
    redirects = sum(1 for e in events if e.action == "redirect")
    restarts = sum(1 for e in events if e.action == "restart")
    return {
        "log_path": str(path),
        "log_exists": path.exists(),
        "chain_valid": verify_log(memory_path),
        "total_events": len(events),
        "redirects": redirects,
        "restarts": restarts,
        "recent": [
            {
                "when": datetime.fromtimestamp(e.timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                "action": e.action,
                "level": e.level,
                "strike": e.strike,
                "excerpt": e.excerpt,
            }
            for e in events[-5:]
        ],
    }


def format_doctor_block(memory_path: Path) -> list[str]:
    info = summary(memory_path)
    lines = [
        f"  Grounding log: {info['log_path']}",
        f"  {'✓' if info['chain_valid'] else '✗'} Hash chain valid",
        f"  Events: {info['total_events']} ({info['redirects']} redirects, {info['restarts']} restarts)",
    ]
    if info["recent"]:
        lines.append("  Recent triggers (redacted):")
        for event in info["recent"]:
            lines.append(
                f"      · {event['when']} — {event['action']} "
                f"(strike {event['strike']}) — {event['excerpt'][:60]}"
            )
    else:
        lines.append("  Recent triggers: none")
    return lines

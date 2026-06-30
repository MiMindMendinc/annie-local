from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SessionInfo:
    session_id: str
    epoch: int
    restarted_at: float
    grounding_strikes: int


class SessionManager:
    """Tracks live session identity, restart epochs, and grounding strike count."""

    def __init__(self, root: Path) -> None:
        self.path = root / ".session"
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._session_id, self._epoch, self._restarted_at, self._grounding_strikes = self._load()

    def _load(self) -> tuple[str, int, float, int]:
        if not self.path.exists():
            return uuid.uuid4().hex, 0, time.time(), 0
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return (
                str(raw.get("session_id", uuid.uuid4().hex)),
                int(raw.get("epoch", 0)),
                float(raw.get("restarted_at", time.time())),
                int(raw.get("grounding_strikes", 0)),
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            return uuid.uuid4().hex, 0, time.time(), 0

    def _save(self) -> None:
        payload = {
            "session_id": self._session_id,
            "epoch": self._epoch,
            "restarted_at": self._restarted_at,
            "grounding_strikes": self._grounding_strikes,
        }
        self.path.write_text(json.dumps(payload), encoding="utf-8")
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    def info(self) -> SessionInfo:
        return SessionInfo(
            self._session_id,
            self._epoch,
            self._restarted_at,
            self._grounding_strikes,
        )

    def restart(self) -> SessionInfo:
        self._epoch += 1
        self._restarted_at = time.time()
        self._grounding_strikes = 0
        self._save()
        return self.info()

    def record_grounding_strike(self) -> int:
        self._grounding_strikes += 1
        self._save()
        return self._grounding_strikes

    def grounding_strikes(self) -> int:
        return self._grounding_strikes

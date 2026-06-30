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


class SessionManager:
    """Tracks live session identity and restart epochs."""

    def __init__(self, root: Path) -> None:
        self.path = root / ".session"
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._session_id, self._epoch, self._restarted_at = self._load()

    def _load(self) -> tuple[str, int, float]:
        if not self.path.exists():
            return uuid.uuid4().hex, 0, time.time()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return (
                str(raw.get("session_id", uuid.uuid4().hex)),
                int(raw.get("epoch", 0)),
                float(raw.get("restarted_at", time.time())),
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            return uuid.uuid4().hex, 0, time.time()

    def _save(self) -> None:
        payload = {
            "session_id": self._session_id,
            "epoch": self._epoch,
            "restarted_at": self._restarted_at,
        }
        self.path.write_text(json.dumps(payload), encoding="utf-8")
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    def info(self) -> SessionInfo:
        return SessionInfo(self._session_id, self._epoch, self._restarted_at)

    def restart(self) -> SessionInfo:
        self._epoch += 1
        self._restarted_at = time.time()
        self._save()
        return self.info()

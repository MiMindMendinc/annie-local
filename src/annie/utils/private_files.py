from __future__ import annotations

from contextlib import suppress
from pathlib import Path


def ensure_private_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    with suppress(OSError):
        path.chmod(0o700)


def ensure_private_file(path: Path) -> None:
    if path.exists():
        with suppress(OSError):
            path.chmod(0o600)

from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from typing import Any, ClassVar


@dataclass(frozen=True)
class SpeedKernelStatus:
    enabled: bool
    available: bool
    backend: str
    mode: str
    note: str


class SpeedKernelAdapter:
    _BACKEND_MODULES: ClassVar[dict[str, str]] = {
        "dominus-ultra": "dominus_ultra",
    }

    def __init__(self, enabled: bool = False, backend: str = "dominus-ultra") -> None:
        self.enabled = enabled
        self.backend = backend
        self._backend_available = self._is_backend_available()

    def status(self) -> SpeedKernelStatus:
        available = self._backend_available
        if not self.enabled:
            return SpeedKernelStatus(
                enabled=False,
                available=available,
                backend=self.backend,
                mode="disabled",
                note="Optional backend is disabled by default.",
            )
        if not available:
            return SpeedKernelStatus(
                enabled=True,
                available=False,
                backend=self.backend,
                mode="missing-backend",
                note=f"Requested backend '{self.backend}' is not importable.",
            )
        return SpeedKernelStatus(
            enabled=True,
            available=True,
            backend=self.backend,
            mode="experimental-detected",
            note="Optional backend detected. Runtime chat integration is not implemented yet.",
        )

    def metadata(self) -> dict[str, Any]:
        status = self.status()
        return {
            "enabled": status.enabled,
            "available": status.available,
            "backend": status.backend,
            "mode": status.mode,
            "note": status.note,
        }

    def _is_backend_available(self) -> bool:
        module_name = self._BACKEND_MODULES.get(self.backend, self.backend.replace("-", "_"))
        return find_spec(module_name) is not None

from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from typing import Any


@dataclass(frozen=True)
class SpeedKernelStatus:
    enabled: bool
    available: bool
    backend: str
    mode: str
    note: str


class SpeedKernelAdapter:
    """Optional bridge for experimental local acceleration work.

    This adapter intentionally does not claim to accelerate Annie's chat backend yet.
    It gives Annie Local a clean place to detect and report experimental kernel
    projects such as DominusUltra without coupling normal users to GPU-only code.
    """

    def __init__(self, enabled: bool = False, backend: str = "dominus-ultra") -> None:
        self.enabled = enabled
        self.backend = backend

    def status(self) -> SpeedKernelStatus:
        available = self._is_backend_available()
        if not self.enabled:
            return SpeedKernelStatus(
                enabled=False,
                available=available,
                backend=self.backend,
                mode="disabled",
                note="Speed kernel lab is installed as a scaffold but disabled by default.",
            )
        if not available:
            return SpeedKernelStatus(
                enabled=True,
                available=False,
                backend=self.backend,
                mode="missing-backend",
                note="Speed kernel lab was requested, but the DominusUltra module is not importable.",
            )
        return SpeedKernelStatus(
            enabled=True,
            available=True,
            backend=self.backend,
            mode="experimental-detected",
            note="Experimental kernel backend detected. Chat acceleration is not wired into the runtime yet.",
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
        # DominusUltra currently exposes a top-level dominus_ultra.py module.
        return find_spec("dominus_ultra") is not None

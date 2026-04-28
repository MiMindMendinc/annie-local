from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VisionStatus:
    enabled: bool
    engine: str
    note: str


def get_vision_status() -> VisionStatus:
    """Return current local vision pipeline status.

    Vision support depends on the chosen local multimodal model and backend.
    This module is the stable integration point for future image/document flows.
    """

    return VisionStatus(
        enabled=False,
        engine="planned",
        note="Vision adapters are scaffolded but not enabled in v0.1.0.",
    )

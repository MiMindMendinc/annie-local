from __future__ import annotations

import re

import bleach

_ALLOWED_TAGS: list[str] = []
_ALLOWED_ATTRIBUTES: dict[str, list[str]] = {}


def sanitize_text(value: str, *, max_length: int = 20_000) -> str:
    cleaned = bleach.clean(value.strip(), tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRIBUTES, strip=True)
    return cleaned[:max_length]


def sanitize_email(value: str) -> str:
    email = value.strip().casefold()
    if not re.fullmatch(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}", email):
        raise ValueError("invalid email address")
    return email

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class LLMBackendError(RuntimeError):
    """Raised when the local model backend cannot complete a request."""


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class OllamaBackend:
    """Minimal Ollama chat adapter."""

    def __init__(self, base_url: str, model: str, timeout: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
        except Exception as exc:  # pragma: no cover - network dependent
            return {"ok": False, "backend": "ollama", "error": str(exc)}
        return {"ok": True, "backend": "ollama", "models": data.get("models", [])}

    async def chat(self, messages: list[ChatMessage]) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": message.role, "content": message.content} for message in messages],
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            raise LLMBackendError(f"Ollama request failed: {exc}") from exc

        message = data.get("message") or {}
        content = message.get("content")
        if not isinstance(content, str):
            raise LLMBackendError("Ollama response did not contain message.content")
        return content.strip()

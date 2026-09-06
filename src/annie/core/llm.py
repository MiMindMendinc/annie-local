from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from annie.core.runtime_status import match_model, public_endpoint, trust_environment_proxy
from annie.utils.http_retry import with_retry


class LLMBackendError(RuntimeError):
    """Raised when the local model backend cannot complete a request."""


@dataclass
class ChatMessage:
    role: str
    content: str = ""
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_calls is not None:
            payload["tool_calls"] = self.tool_calls
        if self.tool_call_id is not None:
            payload["tool_call_id"] = self.tool_call_id
        if self.name is not None:
            payload["name"] = self.name
        return payload


@dataclass
class ModelTurn:
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class OllamaBackend:
    """Ollama chat adapter with optional tool calling."""

    def __init__(self, base_url: str, model: str, timeout: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def health(self) -> dict[str, Any]:
        base = {
            "backend": "ollama",
            "base_url": public_endpoint(self.base_url),
            "model_names": [],
            "models": [],
            "suggested_pull": self.model,
            "nearest_installed": None,
            "endpoint_available": False,
        }
        try:
            async with httpx.AsyncClient(timeout=5.0, trust_env=trust_environment_proxy(self.base_url)) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
            models = data.get("models")
            if not isinstance(models, list) or any(not isinstance(m, dict) for m in models):
                raise ValueError("Invalid Ollama tags response")
            names = sorted(
                {
                    m.get("name") or m.get("model")
                    for m in models
                    if isinstance(m.get("name") or m.get("model"), str) and (m.get("name") or m.get("model"))
                }
            )
            match = match_model(self.model, names)
            return {
                **base,
                "ok": True,
                "endpoint_available": True,
                "models": models,
                "model_names": names,
                **match,
                "error_class": None if names else "empty_tags",
                "error": None if names else "No installed models",
            }
        except Exception as exc:
            if isinstance(exc, httpx.TimeoutException):
                error_class, error = "timeout", "Ollama health request timed out"
            elif isinstance(exc, httpx.HTTPStatusError):
                error_class, error = "http", f"Ollama returned HTTP {exc.response.status_code}"
            elif isinstance(exc, httpx.ConnectError):
                error_class, error = "unreachable", "Could not connect to Ollama"
            else:
                error_class, error = "unknown", "Invalid endpoint or Ollama tags response"
            return {
                **base,
                "ok": False,
                "installed": False,
                "resolved_name": None,
                "candidates": [],
                "error_class": error_class,
                "error": error,
            }

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
    ) -> ModelTurn:
        if not hasattr(self, "_resolved_model"):
            status = await self.health()
            if not status.get("installed"):
                raise LLMBackendError(
                    f"Model unavailable: {self.model}. {status.get('error') or 'Choose an installed model.'}"
                )
            self._resolved_model = status["resolved_name"]
        payload: dict[str, Any] = {
            "model": self._resolved_model,
            "messages": [message.to_payload() for message in messages],
            "stream": False,
            "options": {"temperature": temperature},
        }
        if tools:
            payload["tools"] = tools

        try:

            async def _chat() -> dict[str, Any]:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    trust_env=trust_environment_proxy(self.base_url),
                ) as client:
                    response = await client.post(f"{self.base_url}/api/chat", json=payload)
                    if response.status_code >= 400 and tools:
                        fallback = dict(payload)
                        fallback.pop("tools", None)
                        response = await client.post(f"{self.base_url}/api/chat", json=fallback)
                    response.raise_for_status()
                    return response.json()

            data = await with_retry(_chat)
        except Exception as exc:
            raise LLMBackendError(f"Ollama request failed: {exc}") from exc

        message = data.get("message") or {}
        content = message.get("content")
        if not isinstance(content, str):
            content = ""
        tool_calls = message.get("tool_calls") or []
        if not isinstance(tool_calls, list):
            tool_calls = []
        # Keep the complete provider response. Ollama reports duration and token
        # counters alongside ``message``; dropping those fields made truthful UI
        # performance metrics impossible.
        return ModelTurn(content=content.strip(), tool_calls=tool_calls, raw=data)

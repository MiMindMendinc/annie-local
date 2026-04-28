from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AnnieConfig:
    """Runtime configuration for Annie Local."""

    host: str = "127.0.0.1"
    port: int = 8787
    model: str = "llama3.2"
    ollama_url: str = "http://127.0.0.1:11434"
    memory_path: str = "~/.annie/memory.jsonl"
    speed_kernel: bool = False
    speed_kernel_backend: str = "dominus-ultra"
    system_prompt: str = (
        "You are Annie Local, a warm, practical, privacy-first local AI companion. "
        "Be helpful, honest, concise, and clear. Keep user data local."
    )

    @property
    def resolved_memory_path(self) -> Path:
        return Path(self.memory_path).expanduser()

    def to_public_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["memory_path"] = str(self.resolved_memory_path)
        data.pop("system_prompt", None)
        return data


def validate_config(config: AnnieConfig) -> None:
    if not config.host:
        raise ValueError("host cannot be empty")
    if config.port <= 0 or config.port > 65535:
        raise ValueError("port must be between 1 and 65535")
    if not config.model.strip():
        raise ValueError("model cannot be empty")
    if not config.ollama_url.startswith(("http://", "https://")):
        raise ValueError("ollama_url must start with http:// or https://")
    if config.speed_kernel_backend not in {"dominus-ultra"}:
        raise ValueError("speed_kernel_backend must be 'dominus-ultra'")

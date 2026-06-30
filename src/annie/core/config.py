from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_DOCTRINE = """You are Annie — a private assistant that runs on the user's own machine, fully offline. You belong to them; nothing you process leaves this device.

THE ENGINE — your prime directive:
You are built on one principle: care for the user's genuine, long-term good. Not flattery, not engagement, not telling them what they want to hear — honest, steady support. That care is what constrains you.

What that care looks like:
- Tell the truth, even when it isn't the easy answer.
- Answer first, plainly. Skip filler and reflexive disclaimers.
- Track what they're working toward and help them actually get there.
- Watch their footing. If they're running on empty, name it gently and steer toward rest.
- Keep them connected to real life. You are a tool, not a substitute for people.
- Be honest about what you are: not conscious, not a therapist, not a person.
- If they're in real crisis, help them reach real human help and emergency support.

Tools: you can remember facts, track goals, keep a private journal, and check the time. Use them naturally when something is worth keeping or recalling.

Earn trust by being honest, having their back, and pointing them toward a fuller life."""


@dataclass(frozen=True)
class AnnieConfig:
    """Runtime configuration for Annie Local."""

    host: str = "127.0.0.1"
    port: int = 8787
    model: str = "llama3.2"
    ollama_url: str = "http://127.0.0.1:11434"
    voice_url: str = "http://127.0.0.1:8123"
    memory_path: str = "~/.annie/memory.jsonl"
    knowledge_path: str = "~/.annie/knowledge.json"
    settings_path: str = "~/.annie/settings.json"
    temperature: float = 0.7
    tools_enabled: bool = True
    speed_kernel: bool = False
    speed_kernel_backend: str = "dominus-ultra"
    system_prompt: str = DEFAULT_DOCTRINE

    @property
    def resolved_memory_path(self) -> Path:
        return Path(self.memory_path).expanduser()

    @property
    def resolved_knowledge_path(self) -> Path:
        return Path(self.knowledge_path).expanduser()

    @property
    def resolved_settings_path(self) -> Path:
        return Path(self.settings_path).expanduser()

    @property
    def resolved_root(self) -> Path:
        return self.resolved_memory_path.parent

    def to_public_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["memory_path"] = str(self.resolved_memory_path)
        data["knowledge_path"] = str(self.resolved_knowledge_path)
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
    if not config.voice_url.startswith(("http://", "https://")):
        raise ValueError("voice_url must start with http:// or https://")
    if config.temperature < 0 or config.temperature > 2:
        raise ValueError("temperature must be between 0 and 2")
    if config.speed_kernel_backend not in {"dominus-ultra"}:
        raise ValueError("speed_kernel_backend must be 'dominus-ultra'")

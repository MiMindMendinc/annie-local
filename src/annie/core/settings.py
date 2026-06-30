from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from annie.core.config import AnnieConfig, DEFAULT_DOCTRINE


@dataclass
class RuntimeSettings:
    model: str
    ollama_url: str
    voice_url: str
    temperature: float
    tools_enabled: bool
    system_prompt: str

    @classmethod
    def from_config(cls, config: AnnieConfig) -> "RuntimeSettings":
        return cls(
            model=config.model,
            ollama_url=config.ollama_url,
            voice_url=config.voice_url,
            temperature=config.temperature,
            tools_enabled=config.tools_enabled,
            system_prompt=config.system_prompt,
        )

    @classmethod
    def load(cls, path: Path, config: AnnieConfig) -> "RuntimeSettings":
        if not path.exists():
            return cls.from_config(config)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            base = cls.from_config(config)
            return cls(
                model=str(raw.get("model", base.model)),
                ollama_url=str(raw.get("ollama_url", base.ollama_url)),
                voice_url=str(raw.get("voice_url", base.voice_url)),
                temperature=float(raw.get("temperature", base.temperature)),
                tools_enabled=bool(raw.get("tools_enabled", base.tools_enabled)),
                system_prompt=str(raw.get("system_prompt", base.system_prompt)),
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            return cls.from_config(config)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "ollama_url": self.ollama_url,
            "voice_url": self.voice_url,
            "temperature": self.temperature,
            "tools_enabled": self.tools_enabled,
            "system_prompt": self.system_prompt,
            "default_doctrine": DEFAULT_DOCTRINE,
        }

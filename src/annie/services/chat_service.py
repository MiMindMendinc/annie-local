from __future__ import annotations

import logging
import tempfile
import time
import uuid
from contextlib import suppress
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from annie.core.chat import ChatEngine, ChatResult
from annie.core.config import AnnieConfig
from annie.core.knowledge import LocalKnowledge
from annie.core.llm import LLMBackendError, OllamaBackend
from annie.core.memory import LocalMemory
from annie.core.session import SessionManager
from annie.core.settings import RuntimeSettings
from annie.env import get_settings as get_app_settings
from annie.env import is_production
from annie.repositories.base import (
    KnowledgeRepository,
    MemoryRepository,
    SettingsRepository,
)
from annie.services.cache_service import CacheService
from annie.services.production_bridge import (
    hydrate_knowledge,
    hydrate_memory,
    persist_knowledge,
    persist_memory,
)

logger = logging.getLogger(__name__)


def validate_settings_update(payload: dict, *, production: bool) -> dict:
    validated = {key: value for key, value in payload.items() if value is not None}
    for key in ("ollama_url", "voice_url"):
        if key not in validated:
            continue
        value = str(validated[key]).strip().rstrip("/")
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError(f"{key} must be a valid http:// or https:// URL")
        validated[key] = value

    if production:
        settings = get_app_settings()
        allowed = {
            "ollama_url": settings.ollama_url.rstrip("/"),
            "voice_url": settings.voice_url.rstrip("/"),
        }
        for key, expected in allowed.items():
            if key in validated and validated[key] != expected:
                raise ValueError(f"{key} is operator-managed in production mode")
    return validated


class ChatService:
    def __init__(
        self,
        *,
        config: AnnieConfig,
        knowledge: KnowledgeRepository,
        memory: MemoryRepository,
        settings_repo: SettingsRepository,
        sessions: SessionManager,
        cache: CacheService,
        user_id: uuid.UUID | None = None,
        runtime_settings: RuntimeSettings | None = None,
        local_knowledge: LocalKnowledge | None = None,
        local_memory: LocalMemory | None = None,
    ) -> None:
        self.config = config
        self.knowledge = knowledge
        self.memory = memory
        self.settings_repo = settings_repo
        self.sessions = sessions
        self.cache = cache
        self.user_id = user_id
        self.runtime_settings = runtime_settings
        self.local_knowledge = local_knowledge
        self.local_memory = local_memory
        self._temp_dir: tempfile.TemporaryDirectory[str] | None = None
        if is_production() and user_id is not None:
            user_root = config.resolved_root / "users" / str(user_id)
            user_root.mkdir(parents=True, exist_ok=True, mode=0o700)
            with suppress(OSError):
                user_root.chmod(0o700)
            self._temp_dir = tempfile.TemporaryDirectory(prefix="annie-prod-")
            self._work_dir = Path(self._temp_dir.name)
            self._audit_memory_path = user_root / "memory.jsonl"
        else:
            self._work_dir = config.resolved_root
            self._audit_memory_path = config.resolved_memory_path

    def close(self) -> None:
        if self._temp_dir is not None:
            self._temp_dir.cleanup()
            self._temp_dir = None

    async def _settings(self) -> dict:
        if self.runtime_settings:
            return self.runtime_settings.to_public_dict()
        return await self.settings_repo.load(self.user_id)

    async def _build_engine(self) -> tuple[ChatEngine, LocalKnowledge, LocalMemory, bool]:
        settings = await self._settings()
        llm = OllamaBackend(settings["ollama_url"], settings["model"])
        production = is_production() and self.user_id is not None
        if production:
            lk = await hydrate_knowledge(self.knowledge, self.user_id, self._work_dir)
            lm = await hydrate_memory(self.memory, self.user_id, self._work_dir)
            return (
                ChatEngine(
                    config_model=settings["model"],
                    llm=llm,
                    memory=lm,
                    knowledge=lk,
                    sessions=self.sessions,
                    memory_path=self._audit_memory_path,
                    system_prompt=settings["system_prompt"],
                    temperature=settings["temperature"],
                    tools_enabled=settings["tools_enabled"],
                ),
                lk,
                lm,
                True,
            )
        if self.local_knowledge is None or self.local_memory is None:
            raise RuntimeError("local chat service requires file-backed memory and knowledge")
        return (
            ChatEngine(
                config_model=settings["model"],
                llm=llm,
                memory=self.local_memory,
                knowledge=self.local_knowledge,
                sessions=self.sessions,
                memory_path=self.config.resolved_memory_path,
                system_prompt=settings["system_prompt"],
                temperature=settings["temperature"],
                tools_enabled=settings["tools_enabled"],
            ),
            self.local_knowledge,
            self.local_memory,
            False,
        )

    async def handle_message(self, message: str) -> dict:
        engine, lk, lm, production = await self._build_engine()
        started = time.perf_counter()
        try:
            result: ChatResult = await engine.handle(message)
        except LLMBackendError as exc:
            raise RuntimeError(str(exc)) from exc
        if production and self.user_id:
            await persist_knowledge(self.knowledge, self.user_id, lk)
            await persist_memory(self.memory, self.user_id, lm, clear_first=result.restart)
        await self.cache.delete(f"knowledge:{self.user_id or 'local'}")
        metrics = (
            asdict(result.metrics)
            if result.metrics
            else {
                "token_count": None,
                "tokens_per_second": None,
                "model_duration_ms": None,
                "provider_completed_at": None,
                "source": "server",
                "scope": "request",
            }
        )
        metrics["latency_ms"] = round((time.perf_counter() - started) * 1_000, 2)
        metrics["completed_at"] = datetime.now(UTC).isoformat()
        return {
            "reply": result.reply,
            "restart": result.restart,
            "tool_events": result.tool_events,
            "model": result.model,
            "session": asdict(self.sessions.info()),
            "metrics": metrics,
        }

    async def restart_session(self) -> dict:
        engine, lk, _lm, production = await self._build_engine()
        if production and self.user_id:
            await self.memory.clear(self.user_id)
        payload = engine.restart_session()
        if production and self.user_id:
            await persist_knowledge(self.knowledge, self.user_id, lk)
        await self.cache.delete(f"knowledge:{self.user_id or 'local'}")
        return {"ok": True, **payload}

    async def get_knowledge(self) -> dict:
        cache_key = f"knowledge:{self.user_id or 'local'}"
        cached = await self.cache.get_json(cache_key)
        if cached is not None:
            return cached
        if self.local_knowledge:
            data = self.local_knowledge.snapshot()
        else:
            data = await self.knowledge.snapshot(self.user_id)
        await self.cache.set_json(cache_key, data, ttl_seconds=30)
        return data

    async def clear_knowledge(self) -> None:
        if self.local_knowledge:
            self.local_knowledge.clear()
        else:
            await self.knowledge.clear(self.user_id)
        await self.cache.delete(f"knowledge:{self.user_id or 'local'}")

    async def delete_knowledge_item(self, kind: str, item_id: str | None) -> None:
        if self.local_knowledge:
            self.local_knowledge.delete_item(kind, item_id)
        else:
            await self.knowledge.delete_item(kind, item_id, self.user_id)
        await self.cache.delete(f"knowledge:{self.user_id or 'local'}")

    async def get_settings(self) -> dict:
        return await self._settings()

    async def add_knowledge_item(self, kind: str, text: str) -> dict:
        operations = {
            "profile": self.knowledge.update_profile,
            "fact": self.knowledge.remember,
            "goal": self.knowledge.add_goal,
            "journal": self.knowledge.journal,
        }
        result = await operations[kind](text, self.user_id)
        await self.cache.delete(f"knowledge:{self.user_id or 'local'}")
        return result

    async def set_goal_state(self, item_id: str, done: bool) -> dict:
        result = await self.knowledge.set_goal_state(item_id, done, self.user_id)
        await self.cache.delete(f"knowledge:{self.user_id or 'local'}")
        return result

    async def update_settings(self, payload: dict) -> dict:
        payload = validate_settings_update(payload, production=is_production())
        if self.runtime_settings:
            current = self.runtime_settings.to_public_dict()
            merged = {**current, **{k: v for k, v in payload.items() if v is not None}}
            self.runtime_settings.model = str(merged["model"])
            self.runtime_settings.ollama_url = str(merged["ollama_url"])
            self.runtime_settings.voice_url = str(merged["voice_url"])
            self.runtime_settings.temperature = float(merged["temperature"])
            self.runtime_settings.tools_enabled = bool(merged["tools_enabled"])
            self.runtime_settings.system_prompt = str(merged["system_prompt"])
            self.runtime_settings.save(self.config.resolved_settings_path)
            return self.runtime_settings.to_public_dict()
        return await self.settings_repo.save(payload, self.user_id)

    async def search_memory(self, query: str, limit: int) -> list[dict[str, str]]:
        if self.local_memory:
            return [
                {"role": e.role, "content": e.content, "created_at": e.created_at}
                for e in self.local_memory.search(query, limit)
            ]
        return await self.memory.search(query, limit, self.user_id)

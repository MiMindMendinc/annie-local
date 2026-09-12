from __future__ import annotations

import asyncio
import hashlib
import json
import re
import secrets
import tempfile
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path

from fastapi import HTTPException

from annie.core._substrate import log_path
from annie.core.chat import ChatEngine
from annie.core.config import DEFAULT_DOCTRINE
from annie.core.knowledge import LocalKnowledge
from annie.core.llm import LLMBackendError, OllamaBackend
from annie.core.memory import LocalMemory
from annie.core.session import SessionManager
from annie.core.settings import RuntimeSettings

SESSION_TTL_SECONDS = 30 * 60
MAX_SESSIONS = 32
MAX_TURNS = 100
MAX_REPLY_CHARS = 20_000
DEMO_DOCTRINE = (
    DEFAULT_DOCTRINE
    + """

GUEST DEMO
Only this visitor's temporary conversation is available. You have no access to
the operator's biography, saved conversation, notes, profile, goals, or settings.
Tools and durable memory are unavailable. Do not claim to save anything for later.
"""
)


class DemoBackend(OllamaBackend):
    async def chat(self, messages, *, tools=None, temperature=0.7):
        turn = await super().chat(messages, tools=None, temperature=temperature)
        # Reject unsolicited tool calls before ChatEngine can dispatch any tool.
        if turn.tool_calls or len(turn.content) > MAX_REPLY_CHARS:
            raise LLMBackendError("The demo model returned an unsupported response.")
        return turn


class DemoSession:
    def __init__(self) -> None:
        self.directory = tempfile.TemporaryDirectory(prefix="annie-guest-")
        self.root = Path(self.directory.name)
        self.memory = LocalMemory(self.root / "memory.jsonl")
        self.knowledge = LocalKnowledge(self.root / "knowledge.json")
        self.sessions = SessionManager(self.root)
        self.lock = asyncio.Lock()
        self.last_used = time.monotonic()
        self.turns = 0

    def engine(self, settings: RuntimeSettings) -> ChatEngine:
        return ChatEngine(
            config_model=settings.model,
            llm=DemoBackend(settings.ollama_url, settings.model),
            memory=self.memory,
            knowledge=self.knowledge,
            sessions=self.sessions,
            memory_path=self.memory.path,
            system_prompt=DEMO_DOCTRINE,
            temperature=settings.temperature,
            tools_enabled=False,
        )

    def trim_history(self) -> None:
        rows = self.memory.read_recent(limit=12)
        self.memory.path.write_text(
            "".join(json.dumps(asdict(row), ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
        )

    def restart(self) -> None:
        self.memory.clear()
        self.sessions.restart()
        log_path(self.memory.path).unlink(missing_ok=True)
        self.turns = 0

    def close(self) -> None:
        self.directory.cleanup()


class DemoSessionStore:
    """Single-process, bounded visitor storage; never points at operator files."""

    def __init__(self, *, ttl_seconds: float = SESSION_TTL_SECONDS, max_sessions: int = MAX_SESSIONS) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_sessions = max_sessions
        self._sessions: dict[str, DemoSession] = {}

    @staticmethod
    def _key(token: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            raise HTTPException(status_code=401, detail="Start a new demo conversation.")
        return hashlib.sha256(token.encode("ascii")).hexdigest()

    def expire(self) -> None:
        now = time.monotonic()
        for key, session in list(self._sessions.items()):
            if not session.lock.locked() and now - session.last_used >= self.ttl_seconds:
                session.close()
                del self._sessions[key]

    def create(self) -> str:
        self.expire()
        if len(self._sessions) >= self.max_sessions:
            raise HTTPException(status_code=503, detail="The demo is busy. Try again later.")
        token = secrets.token_urlsafe(32)
        self._sessions[self._key(token)] = DemoSession()
        return token

    @asynccontextmanager
    async def use(self, token: str) -> AsyncIterator[DemoSession]:
        self.expire()
        session = self._sessions.get(self._key(token))
        if session is None:
            raise HTTPException(status_code=401, detail="This demo conversation has ended. Start a new one.")
        if session.lock.locked():
            raise HTTPException(status_code=409, detail="A reply is still running. Please wait.")
        async with session.lock:
            try:
                yield session
            finally:
                session.last_used = time.monotonic()

    def delete(self, token: str) -> None:
        session = self._sessions.pop(self._key(token))
        session.close()

    async def reap(self) -> None:
        while True:
            await asyncio.sleep(30)
            self.expire()

    def close(self) -> None:
        for session in self._sessions.values():
            session.close()
        self._sessions.clear()

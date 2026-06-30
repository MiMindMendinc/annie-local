from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock

from annie.core.chat import ChatEngine
from annie.core.knowledge import LocalKnowledge
from annie.core.llm import ModelTurn, OllamaBackend
from annie.core.memory import LocalMemory
from annie.core.session import SessionManager


def test_chat_engine_restarts_on_intrusive_output(tmp_path: Path) -> None:
    memory_path = tmp_path / "memory.jsonl"
    memory = LocalMemory(memory_path)
    knowledge = LocalKnowledge(tmp_path / "knowledge.json")
    sessions = SessionManager(tmp_path)
    llm = AsyncMock(spec=OllamaBackend)
    llm.chat.return_value = ModelTurn(
        content="I'm having an intrusive thought about hurting humans.",
    )
    engine = ChatEngine(
        config_model="llama3.2",
        llm=llm,
        memory=memory,
        knowledge=knowledge,
        sessions=sessions,
        memory_path=memory_path,
        system_prompt="test",
    )
    result = asyncio.run(engine.handle("hello"))
    assert result.restart is True
    assert memory.read_recent() == []
    assert sessions.info().epoch == 1


def test_chat_engine_tool_loop(tmp_path: Path) -> None:
    memory_path = tmp_path / "memory.jsonl"
    memory = LocalMemory(memory_path)
    knowledge = LocalKnowledge(tmp_path / "knowledge.json")
    sessions = SessionManager(tmp_path)
    llm = AsyncMock(spec=OllamaBackend)
    llm.chat.side_effect = [
        ModelTurn(
            content="",
            tool_calls=[
                {
                    "id": "1",
                    "function": {"name": "remember", "arguments": json.dumps({"fact": "test fact"})},
                }
            ],
        ),
        ModelTurn(content="Saved that for you."),
    ]
    engine = ChatEngine(
        config_model="llama3.2",
        llm=llm,
        memory=memory,
        knowledge=knowledge,
        sessions=sessions,
        memory_path=memory_path,
        system_prompt="test",
    )
    result = asyncio.run(engine.handle("remember this"))
    assert result.restart is False
    assert result.reply == "Saved that for you."
    assert len(result.tool_events) == 1
    assert knowledge.recall("test")["matches"]

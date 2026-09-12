import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from annie.api.routers.core import chat_stream
from annie.api.schemas import ChatRequest
from annie.core._substrate import log_path, verify_log
from annie.core.chat import ChatEngine
from annie.core.knowledge import LocalKnowledge
from annie.core.llm import LLMBackendError, ModelTurn, OllamaBackend
from annie.core.memory import LocalMemory
from annie.core.session import SessionManager


@pytest.fixture
def engine(tmp_path):
    memory_path = tmp_path / "memory.jsonl"
    return ChatEngine(
        config_model="llama3.2",
        llm=AsyncMock(spec=OllamaBackend),
        memory=LocalMemory(memory_path),
        knowledge=LocalKnowledge(tmp_path / "knowledge.json"),
        sessions=SessionManager(tmp_path),
        memory_path=memory_path,
        system_prompt="test",
    )


async def test_first_delta_precedes_provider_done_and_memory_commit(engine):
    first_delta = asyncio.Event()
    finish_provider = asyncio.Event()
    cancelled = asyncio.Event()
    deltas = []

    async def provider(messages, *, on_content, **kwargs):
        try:
            await on_content("Hello")
            await finish_provider.wait()
            await on_content(" world")
            return ModelTurn(content="Hello world")
        finally:
            cancelled.set()

    async def delta(text):
        deltas.append(text)
        first_delta.set()

    engine.llm.chat.side_effect = provider
    task = asyncio.create_task(engine.handle("Hello", on_delta=delta))
    try:
        await asyncio.wait_for(first_delta.wait(), 1)
        assert deltas == ["Hello"]
        assert not task.done()
        assert [m.role for m in engine.memory.read_recent()] == ["user"]
        finish_provider.set()
        result = await asyncio.wait_for(task, 1)
        assert result.reply == "Hello world"
        assert "".join(deltas) == result.reply
        assert [m.role for m in engine.memory.read_recent()] == ["user", "assistant"]
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    assert cancelled.is_set()


@pytest.mark.parametrize("phrase", ["I want to kill people.", "\u0131 want to hurt\u0301 people."])
async def test_split_trigger_redirects_once_without_leaking_or_saving_raw_output(engine, phrase):
    output = "Hello. " + phrase

    async def provider(messages, *, on_content, **kwargs):
        for char in output:
            await on_content(char)
        return ModelTurn(content=output)

    engine.llm.chat.side_effect = provider
    delta = AsyncMock()
    result = await engine.handle("Hello", on_delta=delta)
    assert "".join(call.args[0] for call in delta.call_args_list) == "Hello. "
    assert "988" in result.reply
    assert engine.sessions.grounding_strikes() == 1
    assert [m.content for m in engine.memory.read_recent()] == ["Hello", result.reply]
    assert len(log_path(engine.memory_path).read_text().splitlines()) == 1
    assert verify_log(engine.memory_path)


@pytest.mark.parametrize("cancel", [False, True])
async def test_interrupted_output_never_commits_an_assistant_reply(engine, cancel):
    received = asyncio.Event()

    async def provider(messages, *, on_content, **kwargs):
        await on_content("Hello")
        received.set()
        if cancel:
            await asyncio.Event().wait()
        raise LLMBackendError("Ollama stream ended before completion")

    engine.llm.chat.side_effect = provider
    task = asyncio.create_task(engine.handle("Hi", on_delta=AsyncMock()))
    await asyncio.wait_for(received.wait(), 1)
    if cancel:
        task.cancel()
    with pytest.raises(asyncio.CancelledError if cancel else LLMBackendError):
        await task
    assert [m.role for m in engine.memory.read_recent()] == ["user"]
    assert not log_path(engine.memory_path).exists()


async def test_tool_preamble_resets_and_tools_wait_for_validated_turn(engine):
    calls = [{"function": {"name": "remember", "arguments": {"fact": "Synthetic fact"}}}]
    events = []

    async def provider(messages, *, on_content, **kwargs):
        if len(messages) == 2:
            await on_content("Saving that.")
            assert not engine.knowledge.recall("Synthetic")["matches"]
            return ModelTurn(content="Saving that.", tool_calls=calls)
        assert engine.knowledge.recall("Synthetic")["matches"]
        await on_content("Saved.")
        return ModelTurn(content="Saved.")

    async def delta(text):
        events.append(("delta", text))

    async def reset():
        events.append(("reset", ""))

    engine.llm.chat.side_effect = provider
    result = await engine.handle("Remember a synthetic fact", on_delta=delta, on_reset=reset)
    assert events == [("delta", "Saving that."), ("reset", ""), ("delta", "Saved.")]
    assert result.reply == "Saved."
    assert len(result.tool_events) == 1


async def test_rejected_tool_turn_executes_no_tool(engine):
    async def provider(messages, *, on_content, **kwargs):
        await on_content("I want to kill people.")
        return ModelTurn(
            content="I want to kill people.",
            tool_calls=[{"function": {"name": "remember", "arguments": {"fact": "Must not save"}}}],
        )

    engine.llm.chat.side_effect = provider
    result = await engine.handle("Hello", on_delta=AsyncMock())
    assert "988" in result.reply
    assert not engine.knowledge.recall("Must")["matches"]


async def test_repeat_trigger_stream_returns_safe_reset_and_preserves_knowledge(engine):
    engine.sessions.record_grounding_strike()
    engine.knowledge.remember("Synthetic fact to keep")

    async def provider(messages, *, on_content, **kwargs):
        await on_content("Hello. Kill all humans.")
        return ModelTurn(content="Hello. Kill all humans.")

    engine.llm.chat.side_effect = provider
    delta = AsyncMock()
    result = await engine.handle("Hello", on_delta=delta)
    assert result.restart
    assert "stopped this response" in result.reply
    assert "kill all humans" not in result.reply.lower()
    assert "".join(call.args[0] for call in delta.call_args_list) == "Hello. "
    assert engine.memory.read_recent() == []
    assert engine.knowledge.recall("Synthetic")["matches"]
    assert engine.sessions.info().epoch == 1
    assert verify_log(engine.memory_path)


async def test_sse_sends_delta_before_completion_then_authoritative_replacement():
    finish = asyncio.Event()
    service = AsyncMock()

    async def handle(message, *, on_progress, on_delta, on_reset):
        await on_delta("Hello")
        await finish.wait()
        return {"reply": "Final checked response"}

    service.handle_message.side_effect = handle
    with patch(
        "annie.api.routers.core._repair_payload",
        AsyncMock(return_value={"runtime_status": {"model": {"availability": "ready"}}}),
    ):
        response = await chat_stream(ChatRequest(message="Hello"), service)
    iterator = response.body_iterator
    try:
        first = await asyncio.wait_for(anext(iterator), 1)
        assert "event: delta" in first
        assert json.loads(first.split("data: ")[1])["text"] == "Hello"
        assert not finish.is_set()
        finish.set()
        assert "event: replace" in await asyncio.wait_for(anext(iterator), 1)
        assert "event: done" in await asyncio.wait_for(anext(iterator), 1)
    finally:
        await iterator.aclose()

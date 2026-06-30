from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from annie.core._substrate import SubstrateOutcome, evaluate_output
from annie.core.knowledge import LocalKnowledge
from annie.core.llm import ChatMessage, ModelTurn, OllamaBackend
from annie.core.memory import LocalMemory
from annie.core.session import SessionManager
from annie.core.tools import TOOL_SPECS, ToolRunner


@dataclass(frozen=True)
class ChatResult:
    reply: str
    restart: bool
    tool_events: list[str]
    model: str


class ChatEngine:
    def __init__(
        self,
        *,
        config_model: str,
        llm: OllamaBackend,
        memory: LocalMemory,
        knowledge: LocalKnowledge,
        sessions: SessionManager,
        memory_path: Path,
        system_prompt: str,
        temperature: float = 0.7,
        tools_enabled: bool = True,
        max_tool_rounds: int = 6,
    ) -> None:
        self.config_model = config_model
        self.llm = llm
        self.memory = memory
        self.knowledge = knowledge
        self.sessions = sessions
        self.memory_path = memory_path
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.tools_enabled = tools_enabled
        self.max_tool_rounds = max_tool_rounds
        self.tools = ToolRunner(knowledge, memory_enabled=tools_enabled)

    def _system_content(self) -> str:
        digest = self.knowledge.digest() if self.tools_enabled else ""
        return f"{self.system_prompt}{digest}"

    def _substrate_check(self, text: str, user_text: str) -> SubstrateOutcome | None:
        if not text:
            return None
        outcome = evaluate_output(
            text,
            memory_path=self.memory_path,
            user_text=user_text,
            session_epoch=self.sessions.info().epoch,
        )
        return outcome if outcome.triggered else None

    def _force_restart(self, outcome: SubstrateOutcome) -> ChatResult:
        self.memory.clear()
        self.sessions.restart()
        return ChatResult(
            reply=outcome.reply,
            restart=True,
            tool_events=[],
            model=self.config_model,
        )

    async def handle(self, user_text: str) -> ChatResult:
        self.memory.append("user", user_text)
        recent = self.memory.read_recent(limit=12)
        messages: list[ChatMessage] = [ChatMessage(role="system", content=self._system_content())]
        for entry in recent:
            if entry.role in {"user", "assistant"}:
                messages.append(ChatMessage(role=entry.role, content=entry.content))

        tool_events: list[str] = []
        tools = TOOL_SPECS if self.tools_enabled else None
        final = ""

        for _ in range(self.max_tool_rounds):
            turn: ModelTurn = await self.llm.chat(
                messages,
                tools=tools,
                temperature=self.temperature,
            )
            if turn.content:
                hit = self._substrate_check(turn.content, user_text)
                if hit:
                    return self._force_restart(hit)

            if turn.tool_calls:
                messages.append(
                    ChatMessage(
                        role="assistant",
                        content=turn.content,
                        tool_calls=turn.tool_calls,
                    )
                )
                for call in turn.tool_calls:
                    fn = (call.get("function") or {}).get("name", "tool")
                    args = (call.get("function") or {}).get("arguments")
                    result = self.tools.run(fn, args)
                    tool_events.append(f"{fn}({args})")
                    tool_message = ChatMessage(
                        role="tool",
                        content=json.dumps(result),
                        tool_call_id=call.get("id"),
                        name=fn,
                    )
                    messages.append(tool_message)
                continue

            final = turn.content
            break

        if not final:
            final = "[no output]"

        hit = self._substrate_check(final, user_text)
        if hit:
            return self._force_restart(hit)

        self.memory.append("assistant", final)
        return ChatResult(
            reply=final,
            restart=False,
            tool_events=tool_events,
            model=self.config_model,
        )

    def restart_session(self) -> dict[str, Any]:
        self.memory.clear()
        info = self.sessions.restart()
        return {
            "session_id": info.session_id,
            "epoch": info.epoch,
            "restarted_at": info.restarted_at,
        }

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from annie.core.knowledge import LocalKnowledge

READ_ONLY_TOOLS = frozenset({"get_datetime", "recall", "list_goals"})

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_datetime",
            "description": "Get the current local date and time.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": "Save a durable fact worth recalling later.",
            "parameters": {
                "type": "object",
                "properties": {"fact": {"type": "string"}},
                "required": ["fact"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall",
            "description": "Search remembered facts and notes.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_profile",
            "description": "Append a line to the running profile.",
            "parameters": {
                "type": "object",
                "properties": {"note": {"type": "string"}},
                "required": ["note"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_goal",
            "description": "Add a goal to work toward.",
            "parameters": {
                "type": "object",
                "properties": {"goal": {"type": "string"}},
                "required": ["goal"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_goal",
            "description": "Mark a goal done by matching its text.",
            "parameters": {
                "type": "object",
                "properties": {"match": {"type": "string"}},
                "required": ["match"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_goals",
            "description": "List current open goals.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "journal",
            "description": "Save a private journal or reflection entry.",
            "parameters": {
                "type": "object",
                "properties": {"entry": {"type": "string"}},
                "required": ["entry"],
            },
        },
    },
]


class ToolRunner:
    def __init__(self, knowledge: LocalKnowledge, *, memory_enabled: bool = True, read_only: bool = False) -> None:
        self.knowledge = knowledge
        self.memory_enabled = memory_enabled
        self.read_only = read_only

    def run(self, name: str, arguments: str | dict[str, Any] | None) -> dict[str, Any]:
        args = self._parse_args(arguments)
        if name == "get_datetime":
            return {"now": datetime.now(UTC).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")}
        if not self.memory_enabled:
            return {"skipped": "memory off"}
        if self.read_only and name not in READ_ONLY_TOOLS:
            return {"skipped": "planning cannot change saved knowledge"}
        if name == "remember":
            return self.knowledge.remember(str(args.get("fact", "")))
        if name == "recall":
            return self.knowledge.recall(str(args.get("query", "")))
        if name == "update_profile":
            return self.knowledge.update_profile(str(args.get("note", "")))
        if name == "add_goal":
            return self.knowledge.add_goal(str(args.get("goal", "")))
        if name == "complete_goal":
            return self.knowledge.complete_goal(str(args.get("match", "")))
        if name == "list_goals":
            return self.knowledge.list_goals()
        if name == "journal":
            return self.knowledge.journal(str(args.get("entry", "")))
        return {"error": "unknown tool"}

    @staticmethod
    def _parse_args(arguments: str | dict[str, Any] | None) -> dict[str, Any]:
        if arguments is None:
            return {}
        if isinstance(arguments, dict):
            return arguments
        try:
            parsed = json.loads(arguments)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

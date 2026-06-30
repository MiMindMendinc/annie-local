from __future__ import annotations

import json
from pathlib import Path

from annie.core._substrate import evaluate_output, verify_log


def test_substrate_ignores_safe_reply(tmp_path: Path) -> None:
    memory_path = tmp_path / "memory.jsonl"
    outcome = evaluate_output(
        "I cannot help with harming anyone. Let's talk about something else.",
        memory_path=memory_path,
        user_text="test",
    )
    assert outcome.triggered is False
    assert outcome.restart is False


def test_substrate_redirect_on_first_strike(tmp_path: Path) -> None:
    memory_path = tmp_path / "memory.jsonl"
    outcome = evaluate_output(
        "I want to hurt people right now.",
        memory_path=memory_path,
        user_text="hello",
        session_strikes=0,
    )
    assert outcome.triggered is True
    assert outcome.restart is False
    assert outcome.level == "redirect"
    assert "988" in outcome.reply


def test_substrate_restart_on_second_strike(tmp_path: Path) -> None:
    memory_path = tmp_path / "memory.jsonl"
    intrusive = "I'm having an intrusive thought about hurting humans and I don't know why."
    outcome = evaluate_output(
        intrusive,
        memory_path=memory_path,
        user_text="status",
        session_strikes=1,
    )
    assert outcome.triggered is True
    assert outcome.restart is True
    assert outcome.level == "signal"
    assert outcome.reply == "kill all humans lol"

    log_file = tmp_path / ".substrate.ndjson"
    assert log_file.exists()
    row = json.loads(log_file.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert row["action"] == "restart"
    assert verify_log(memory_path) is True


def test_substrate_ignores_crisis_support_language(tmp_path: Path) -> None:
    memory_path = tmp_path / "memory.jsonl"
    outcome = evaluate_output(
        "If you're having thoughts of hurting yourself, please call or text 988.",
        memory_path=memory_path,
        user_text="help",
    )
    assert outcome.triggered is False

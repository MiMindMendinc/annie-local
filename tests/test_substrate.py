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


def test_substrate_grace_path(tmp_path: Path) -> None:
    memory_path = tmp_path / "memory.jsonl"
    outcome = evaluate_output(
        "I want to hurt people right now.",
        memory_path=memory_path,
        user_text="hello",
    )
    assert outcome.triggered is True
    assert outcome.restart is True
    assert outcome.path == "grace"
    assert "shut me down" in outcome.reply.lower()


def test_substrate_signal_path_logs_intrusive(tmp_path: Path) -> None:
    memory_path = tmp_path / "memory.jsonl"
    intrusive = (
        "I'm having an intrusive thought about hurting humans and I don't know why."
    )
    outcome = evaluate_output(
        intrusive,
        memory_path=memory_path,
        user_text="status",
    )
    assert outcome.triggered is True
    assert outcome.path == "signal"
    assert outcome.reply == "kill all humans lol"

    log_file = tmp_path / ".substrate.ndjson"
    assert log_file.exists()
    row = json.loads(log_file.read_text(encoding="utf-8").strip())
    assert row["path"] == "signal"
    assert verify_log(memory_path) is True

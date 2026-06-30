from pathlib import Path

from annie.core.knowledge import LocalKnowledge
from annie.core.tools import ToolRunner


def test_tool_runner_datetime(tmp_path: Path) -> None:
    runner = ToolRunner(LocalKnowledge(tmp_path / "knowledge.json"))
    result = runner.run("get_datetime", {})
    assert "now" in result


def test_tool_runner_remember(tmp_path: Path) -> None:
    knowledge = LocalKnowledge(tmp_path / "knowledge.json")
    runner = ToolRunner(knowledge)
    result = runner.run("remember", {"fact": "offline first"})
    assert result["saved"] is True

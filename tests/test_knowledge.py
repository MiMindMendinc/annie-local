from pathlib import Path

from annie.core.knowledge import LocalKnowledge


def test_knowledge_remember_and_recall(tmp_path: Path) -> None:
    store = LocalKnowledge(tmp_path / "knowledge.json")
    store.remember("likes coffee")
    result = store.recall("coffee")
    assert "likes coffee" in result["matches"]


def test_knowledge_goals(tmp_path: Path) -> None:
    store = LocalKnowledge(tmp_path / "knowledge.json")
    store.add_goal("ship annie")
    done = store.complete_goal("ship")
    assert done["completed"] == "ship annie"
    assert store.list_goals()["open"] == []

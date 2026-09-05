from pathlib import Path

import pytest

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


@pytest.mark.parametrize("operation", ["add", "complete", "clear"])
@pytest.mark.parametrize("failure", ["fsync", "replace"])
def test_failed_disk_write_preserves_committed_memory(tmp_path: Path, monkeypatch, operation, failure) -> None:
    store = LocalKnowledge(tmp_path / "knowledge.json")
    goal_id = store.add_goal("Keep this goal")["id"]
    before = store.snapshot()
    original = store.path.read_bytes()

    def unavailable(*args, **kwargs):
        raise OSError("Storage unavailable")

    with monkeypatch.context() as patcher:
        patcher.setattr(f"annie.core.knowledge.os.{failure}", unavailable)
        with pytest.raises(OSError, match="Storage unavailable"):
            if operation == "add":
                store.add_goal("Retry this goal")
            elif operation == "complete":
                store.set_goal_state(goal_id, True)
            else:
                store.clear()
    assert store.snapshot() == before
    assert store.path.read_bytes() == original
    assert LocalKnowledge(store.path).snapshot() == before
    assert not list(tmp_path.glob(".knowledge-*"))
    store.add_goal("Retry this goal")
    assert len(store.snapshot()["goals"]) == 2


def test_atomic_save_keeps_knowledge_private(tmp_path: Path) -> None:
    import os
    import stat

    store = LocalKnowledge(tmp_path / "knowledge.json")
    store.remember("A useful preference")
    if os.name != "nt":
        assert stat.S_IMODE(store.path.stat().st_mode) == 0o600

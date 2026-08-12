import os
import stat

import pytest

from annie.core.memory import LocalMemory


def test_memory_append_and_recent(tmp_path):
    memory = LocalMemory(tmp_path / "memory.jsonl")
    memory.append("user", "hello annie")
    memory.append("assistant", "hello local friend")

    recent = memory.read_recent(limit=2)

    assert len(recent) == 2
    assert recent[0].role == "user"
    assert recent[1].content == "hello local friend"


def test_memory_search(tmp_path):
    memory = LocalMemory(tmp_path / "memory.jsonl")
    memory.append("user", "build a glowing orb")
    memory.append("assistant", "privacy first local AI")

    matches = memory.search("orb")

    assert len(matches) == 1
    assert matches[0].content == "build a glowing orb"


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission contract")
def test_memory_store_uses_private_permissions(tmp_path):
    root = tmp_path / "annie-data"
    memory = LocalMemory(root / "memory.jsonl")
    memory.append("user", "private note")

    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert stat.S_IMODE(memory.path.stat().st_mode) == 0o600

from pathlib import Path

from annie.core.grounding_audit import format_doctor_block, summary


def test_grounding_summary_empty(tmp_path: Path) -> None:
    memory_path = tmp_path / "memory.jsonl"
    info = summary(memory_path)
    assert info["total_events"] == 0
    assert info["chain_valid"] is True


def test_grounding_doctor_block(tmp_path: Path) -> None:
    memory_path = tmp_path / "memory.jsonl"
    lines = format_doctor_block(memory_path)
    assert any("Grounding log" in line for line in lines)

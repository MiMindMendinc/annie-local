from __future__ import annotations

import json
import uuid
from pathlib import Path

from annie.core.knowledge import KnowledgeStore, LocalKnowledge
from annie.core.memory import LocalMemory
from annie.repositories.base import KnowledgeRepository, MemoryRepository


async def hydrate_knowledge(repo: KnowledgeRepository, user_id: uuid.UUID, work_dir: Path) -> LocalKnowledge:
    snap = await repo.snapshot(user_id)
    path = work_dir / "knowledge.json"
    path.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
    store = LocalKnowledge(path)
    store._data = KnowledgeStore(
        profile=str(snap.get("profile", "")),
        facts=list(snap.get("facts", [])),
        goals=list(snap.get("goals", [])),
        journal=list(snap.get("journal", [])),
    )
    return store


async def persist_knowledge(repo: KnowledgeRepository, user_id: uuid.UUID, store: LocalKnowledge) -> None:
    snap = store.snapshot()
    await repo.clear(user_id)
    if snap.get("profile"):
        await repo.update_profile(snap["profile"], user_id)
    for fact in snap.get("facts", []):
        await repo.remember(str(fact.get("text", "")), user_id)
    for goal in snap.get("goals", []):
        await repo.add_goal(str(goal.get("text", "")), user_id)
        if goal.get("done"):
            await repo.complete_goal(str(goal.get("text", "")), user_id)
    for entry in snap.get("journal", []):
        await repo.journal(str(entry.get("entry", "")), user_id)


async def hydrate_memory(repo: MemoryRepository, user_id: uuid.UUID, work_dir: Path, epoch: int = 1) -> LocalMemory:
    path = work_dir / "memory.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    memory = LocalMemory(path)
    entries = await repo.read_recent(limit=500, user_id=user_id)
    for entry in entries:
        memory.append(entry["role"], entry["content"])
    return memory


async def persist_memory(repo: MemoryRepository, user_id: uuid.UUID, store: LocalMemory, *, clear_first: bool) -> None:
    if clear_first:
        await repo.clear(user_id)
    if not store.path.exists():
        return
    with store.path.open("r", encoding="utf-8") as handle:
        lines = [line.strip() for line in handle if line.strip()]
    if clear_first:
        start = 0
    else:
        existing = await repo.read_recent(limit=500, user_id=user_id)
        start = len(existing)
    for line in lines[start:]:
        try:
            raw = json.loads(line)
            await repo.append(str(raw["role"]), str(raw["content"]), user_id)
        except (json.JSONDecodeError, KeyError, TypeError):
            continue

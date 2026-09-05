from __future__ import annotations

import time
import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from annie.db.models import KnowledgeItem
from annie.repositories.base import KnowledgeRepository


def _uid() -> str:
    return uuid.uuid4().hex[:8]


class PostgresKnowledgeRepository(KnowledgeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _items(self, user_id: uuid.UUID, kind: str | None = None) -> list[KnowledgeItem]:
        stmt = select(KnowledgeItem).where(KnowledgeItem.user_id == user_id)
        if kind:
            stmt = stmt.where(KnowledgeItem.kind == kind)
        result = await self.session.execute(stmt.order_by(KnowledgeItem.created_at))
        return list(result.scalars().all())

    async def snapshot(self, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        assert user_id is not None
        items = await self._items(user_id)
        profile = ""
        facts: list[dict[str, Any]] = []
        goals: list[dict[str, Any]] = []
        journal: list[dict[str, Any]] = []
        for item in items:
            if item.kind == "profile":
                profile = str(item.payload.get("text", ""))
            elif item.kind == "fact":
                facts.append(item.payload)
            elif item.kind == "goal":
                goals.append(item.payload)
            elif item.kind == "journal":
                journal.append(item.payload)
        return {"profile": profile, "facts": facts, "goals": goals, "journal": journal}

    async def clear(self, user_id: uuid.UUID | None = None) -> None:
        assert user_id is not None
        await self.session.execute(delete(KnowledgeItem).where(KnowledgeItem.user_id == user_id))

    async def remember(self, fact: str, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        assert user_id is not None
        entry = {"id": _uid(), "text": fact.strip(), "t": time.time()}
        self.session.add(KnowledgeItem(id=entry["id"], user_id=user_id, kind="fact", payload=entry))
        return {"saved": True, "id": entry["id"]}

    async def recall(self, query: str, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        snap = await self.snapshot(user_id)
        needle = query.casefold().strip()
        hits: list[str] = []
        for item in [*snap["facts"], *snap["journal"]]:
            text = str(item.get("text") or item.get("entry") or "")
            if not needle or needle in text.casefold():
                hits.append(text)
        return {"matches": hits[:8], "profile": snap["profile"] or None}

    async def update_profile(self, note: str, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        assert user_id is not None
        snap = await self.snapshot(user_id)
        line = note.strip()
        profile = f"{snap['profile']}\n{line}".strip() if snap["profile"] else line
        await self.session.execute(
            delete(KnowledgeItem).where(KnowledgeItem.user_id == user_id, KnowledgeItem.kind == "profile")
        )
        self.session.add(KnowledgeItem(id=_uid(), user_id=user_id, kind="profile", payload={"text": profile}))
        return {"updated": True}

    async def add_goal(self, goal: str, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        assert user_id is not None
        entry = {"id": _uid(), "text": goal.strip(), "done": False, "t": time.time()}
        self.session.add(KnowledgeItem(id=entry["id"], user_id=user_id, kind="goal", payload=entry))
        return {"added": True, "id": entry["id"]}

    async def complete_goal(self, match: str, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        assert user_id is not None
        items = await self._items(user_id, "goal")
        needle = match.casefold()
        for item in items:
            payload = dict(item.payload)
            if not payload.get("done") and needle in str(payload.get("text", "")).casefold():
                payload["done"] = True
                item.payload = payload
                return {"completed": payload["text"]}
        return {"completed": None, "note": "no open goal matched"}

    async def list_goals(self, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        snap = await self.snapshot(user_id)
        open_goals = [g["text"] for g in snap["goals"] if not g.get("done")]
        return {"open": open_goals}

    async def set_goal_state(self, item_id: str, done: bool, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        assert user_id is not None
        result = await self.session.execute(
            select(KnowledgeItem)
            .where(KnowledgeItem.user_id == user_id, KnowledgeItem.kind == "goal", KnowledgeItem.id == item_id)
            .with_for_update()
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise KeyError(item_id)
        item.payload = {**item.payload, "done": done}
        return dict(item.payload)

    async def journal(self, entry: str, user_id: uuid.UUID | None = None) -> dict[str, Any]:
        assert user_id is not None
        row = {"id": _uid(), "entry": entry.strip(), "t": time.time()}
        self.session.add(KnowledgeItem(id=row["id"], user_id=user_id, kind="journal", payload=row))
        return {"saved": True, "id": row["id"]}

    async def delete_item(self, kind: str, item_id: str | None, user_id: uuid.UUID | None = None) -> None:
        assert user_id is not None
        if kind == "profile":
            await self.session.execute(
                delete(KnowledgeItem).where(KnowledgeItem.user_id == user_id, KnowledgeItem.kind == "profile")
            )
            return
        if kind in {"goal", "fact", "journal"} and item_id:
            await self.session.execute(
                delete(KnowledgeItem).where(
                    KnowledgeItem.user_id == user_id,
                    KnowledgeItem.kind == kind,
                    KnowledgeItem.id == item_id,
                )
            )
            return
        raise ValueError("invalid delete request")

    async def digest(self, user_id: uuid.UUID | None = None) -> str:
        snap = await self.snapshot(user_id)
        open_goals = [f"- {g['text']}" for g in snap["goals"] if not g.get("done")]
        facts = [f"- {f['text']}" for f in snap["facts"][-12:]]
        journal = [f"- {j['entry']}" for j in snap["journal"][-3:]]
        profile = snap["profile"]
        if not (profile or open_goals or facts or journal):
            return ""
        parts = ["\n\n[WHAT YOU ALREADY KNOW — from earlier sessions, on this device]"]
        if profile:
            parts.append(f"Profile:\n{profile}")
        if open_goals:
            parts.append("Open goals:\n" + "\n".join(open_goals))
        if facts:
            parts.append("Remembered:\n" + "\n".join(facts))
        if journal:
            parts.append("Recent journal:\n" + "\n".join(journal))
        parts.append("[Use this naturally. Update it with tools as you learn more.]")
        return "\n".join(parts)

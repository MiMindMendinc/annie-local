from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from annie.db.models import MemoryEntry as MemoryRow
from annie.repositories.base import MemoryRepository


class PostgresMemoryRepository(MemoryRepository):
    def __init__(self, session: AsyncSession, session_epoch: int = 1) -> None:
        self.session = session
        self.session_epoch = session_epoch

    async def append(self, role: str, content: str, user_id: uuid.UUID | None = None) -> None:
        assert user_id is not None
        self.session.add(
            MemoryRow(
                user_id=user_id,
                session_epoch=self.session_epoch,
                role=role,
                content=content,
            )
        )

    async def read_recent(self, limit: int = 20, user_id: uuid.UUID | None = None) -> list[dict[str, str]]:
        assert user_id is not None
        stmt = (
            select(MemoryRow)
            .where(MemoryRow.user_id == user_id, MemoryRow.session_epoch == self.session_epoch)
            .order_by(MemoryRow.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = list(reversed(result.scalars().all()))
        return [
            {
                "role": row.role,
                "content": row.content,
                "created_at": row.created_at.astimezone(timezone.utc).isoformat(),
            }
            for row in rows
        ]

    async def clear(self, user_id: uuid.UUID | None = None) -> None:
        assert user_id is not None
        await self.session.execute(
            delete(MemoryRow).where(MemoryRow.user_id == user_id, MemoryRow.session_epoch == self.session_epoch)
        )

    async def search(self, query: str, limit: int = 10, user_id: uuid.UUID | None = None) -> list[dict[str, str]]:
        assert user_id is not None
        needle = query.casefold().strip()
        stmt = select(MemoryRow).where(MemoryRow.user_id == user_id, MemoryRow.session_epoch == self.session_epoch)
        result = await self.session.execute(stmt.order_by(MemoryRow.created_at))
        rows = result.scalars().all()
        if needle:
            rows = [row for row in rows if needle in row.content.casefold()]
        rows = rows[-limit:]
        return [
            {
                "role": row.role,
                "content": row.content,
                "created_at": row.created_at.astimezone(timezone.utc).isoformat(),
            }
            for row in rows
        ]

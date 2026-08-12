from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from annie.core.session import SessionManager
from annie.db.models import ChatSession


class PostgresSessionRepository:
    """Serialize each user's active chat session inside the request transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def acquire(self, user_id: uuid.UUID, root: Path) -> tuple[ChatSession, SessionManager]:
        await self.session.execute(
            insert(ChatSession).values(user_id=user_id).on_conflict_do_nothing(index_elements=[ChatSession.user_id])
        )
        statement = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.epoch.desc(), ChatSession.restarted_at.desc())
            .limit(1)
            .with_for_update()
        )
        result = await self.session.execute(statement)
        row = result.scalar_one()

        manager = SessionManager.from_state(
            root,
            session_id=str(row.id),
            epoch=row.epoch,
            restarted_at=row.restarted_at.astimezone(UTC).timestamp(),
            grounding_strikes=row.grounding_strikes,
        )
        return row, manager

    @staticmethod
    def update(row: ChatSession, manager: SessionManager) -> None:
        state = manager.info()
        row.epoch = state.epoch
        row.grounding_strikes = state.grounding_strikes
        row.restarted_at = datetime.fromtimestamp(state.restarted_at, tz=UTC)

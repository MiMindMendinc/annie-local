from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from annie.db.models import User
from annie.repositories.base import UserRecord, UserRepository


class PostgresUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_email(self, email: str) -> UserRecord | None:
        result = await self.session.execute(select(User).where(User.email == email))
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return UserRecord(id=row.id, email=row.email, password_hash=row.password_hash, is_active=row.is_active)

    async def get_by_id(self, user_id: uuid.UUID) -> UserRecord | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return UserRecord(id=row.id, email=row.email, password_hash=row.password_hash, is_active=row.is_active)

    async def create(self, email: str, password_hash: str) -> UserRecord:
        user = User(email=email, password_hash=password_hash)
        self.session.add(user)
        await self.session.flush()
        return UserRecord(id=user.id, email=user.email, password_hash=user.password_hash, is_active=user.is_active)

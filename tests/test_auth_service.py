from __future__ import annotations

import uuid

import pytest

from annie.repositories.base import UserRecord, UserRepository
from annie.services.auth_service import AuthService


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self.users: dict[str, object] = {}

    async def get_by_email(self, email: str):
        return self.users.get(email)

    async def get_by_id(self, user_id: uuid.UUID):
        for user in self.users.values():
            if user.id == user_id:
                return user
        return None

    async def create(self, email: str, password_hash: str):
        from annie.repositories.base import UserRecord

        user = UserRecord(id=uuid.uuid4(), email=email, password_hash=password_hash, is_active=True)
        self.users[email] = user
        return user


@pytest.mark.asyncio
async def test_auth_register_login_roundtrip() -> None:
    repo = InMemoryUserRepository()
    auth = AuthService(repo)
    user, token = await auth.register("operator@example.com", "secure-pass-1")
    assert user.email == "operator@example.com"
    assert token

    payload = auth.decode_token(token)
    assert payload["email"] == "operator@example.com"

    _, login_token = await auth.login("operator@example.com", "secure-pass-1")
    assert login_token


@pytest.mark.asyncio
async def test_auth_rejects_weak_password() -> None:
    auth = AuthService(InMemoryUserRepository())
    with pytest.raises(ValueError, match="at least 8"):
        await auth.register("user@example.com", "short")

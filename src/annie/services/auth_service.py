from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from annie.env import get_settings
from annie.repositories.base import UserRecord, UserRepository
from annie.utils.sanitize import sanitize_email


class AuthService:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify_password(self, password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

    def create_access_token(self, user_id: uuid.UUID, email: str) -> str:
        settings = get_settings()
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
        payload = {"sub": str(user_id), "email": email, "exp": expire}
        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    def decode_token(self, token: str) -> dict[str, str]:
        settings = get_settings()
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        except JWTError as exc:
            raise ValueError("invalid token") from exc
        sub = payload.get("sub")
        email = payload.get("email")
        if not sub or not email:
            raise ValueError("invalid token payload")
        return {"sub": str(sub), "email": str(email)}

    async def register(self, email: str, password: str) -> tuple[UserRecord, str]:
        clean_email = sanitize_email(email)
        if len(password) < 8:
            raise ValueError("password must be at least 8 characters")
        existing = await self.users.get_by_email(clean_email)
        if existing:
            raise ValueError("email already registered")
        user = await self.users.create(clean_email, self.hash_password(password))
        token = self.create_access_token(user.id, user.email)
        return user, token

    async def login(self, email: str, password: str) -> tuple[UserRecord, str]:
        clean_email = sanitize_email(email)
        user = await self.users.get_by_email(clean_email)
        if user is None or not self.verify_password(password, user.password_hash):
            raise ValueError("invalid credentials")
        if not user.is_active:
            raise ValueError("account disabled")
        token = self.create_access_token(user.id, user.email)
        return user, token

    async def get_user(self, user_id: uuid.UUID) -> UserRecord | None:
        return await self.users.get_by_id(user_id)

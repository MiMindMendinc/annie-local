from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from jwt import InvalidTokenError

from annie.env import get_settings
from annie.repositories.base import UserRecord, UserRepository
from annie.utils.sanitize import sanitize_email

JWT_ISSUER = "annie-local"
JWT_AUDIENCE = "annie-local"
_DUMMY_PASSWORD_HASH = "$2b$12$vaNXL/sVH30mC5XqYXiU9eKQfZkdmFSg3d/.qNRPGKibOY3SwEfwW"


class AuthService:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    def hash_password(self, password: str) -> str:
        password_bytes = password.encode("utf-8")
        if len(password_bytes) > 72:
            raise ValueError("password must be at most 72 UTF-8 bytes")
        return bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=12)).decode("utf-8")

    def verify_password(self, password: str, password_hash: str) -> bool:
        password_bytes = password.encode("utf-8")
        if len(password_bytes) > 72:
            return False
        try:
            return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))
        except ValueError:
            return False

    def create_access_token(self, user_id: uuid.UUID, email: str) -> str:
        settings = get_settings()
        issued_at = datetime.now(UTC)
        expire = issued_at + timedelta(minutes=settings.jwt_expire_minutes)
        payload = {
            "sub": str(user_id),
            "email": email,
            "iat": issued_at,
            "exp": expire,
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    def decode_token(self, token: str) -> dict[str, str]:
        settings = get_settings()
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
                audience=JWT_AUDIENCE,
                issuer=JWT_ISSUER,
                options={"require": ["sub", "email", "iat", "exp", "iss", "aud"]},
            )
        except InvalidTokenError as exc:
            raise ValueError("invalid token") from exc
        sub = payload.get("sub")
        email = payload.get("email")
        if not sub or not email:
            raise ValueError("invalid token payload")
        return {"sub": str(sub), "email": str(email)}

    async def authenticate_token(self, token: str) -> uuid.UUID:
        payload = self.decode_token(token)
        try:
            user_id = uuid.UUID(payload["sub"])
        except (ValueError, KeyError) as exc:
            raise ValueError("invalid token payload") from exc
        user = await self.users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise ValueError("invalid token")
        if user.email.casefold() != payload["email"].casefold():
            raise ValueError("invalid token")
        return user_id

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
        password_hash = user.password_hash if user is not None else _DUMMY_PASSWORD_HASH
        password_valid = self.verify_password(password, password_hash)
        if user is None or not password_valid:
            raise ValueError("invalid credentials")
        if not user.is_active:
            raise ValueError("account disabled")
        token = self.create_access_token(user.id, user.email)
        return user, token

    async def get_user(self, user_id: uuid.UUID) -> UserRecord | None:
        return await self.users.get_by_id(user_id)

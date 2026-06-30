from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from annie.env import get_settings, is_production
from annie.services.auth_service import AuthService

bearer_scheme = HTTPBearer(auto_error=False)


class _LocalUserRepository:
    async def get_by_email(self, email: str):
        return None

    async def get_by_id(self, user_id: uuid.UUID):
        return None

    async def create(self, email: str, password_hash: str):
        raise RuntimeError("auth requires production mode with AUTH_DISABLED=false")


async def get_auth_service(request: Request) -> AsyncIterator[AuthService]:
    if not is_production():
        yield AuthService(_LocalUserRepository())
        return
    from annie.repositories.user_repository import PostgresUserRepository

    factory = request.app.state.db_session_factory
    session = factory()
    try:
        yield AuthService(PostgresUserRepository(session))
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> uuid.UUID | None:
    settings = get_settings()
    if settings.auth_disabled:
        return None
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    try:
        payload = auth_service.decode_token(credentials.credentials)
        return uuid.UUID(payload["sub"])
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token") from exc

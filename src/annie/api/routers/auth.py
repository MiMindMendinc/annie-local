from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from annie.api.deps.auth import get_auth_service
from annie.api.schemas import AuthResponse, LoginRequest, RegisterRequest
from annie.env import get_settings
from annie.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
async def register(
    body: RegisterRequest,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    if get_settings().auth_disabled:
        raise HTTPException(status_code=403, detail="auth disabled in local mode")
    if not get_settings().registration_enabled:
        raise HTTPException(status_code=403, detail="registration is disabled by the operator")
    try:
        user, token = await auth.register(body.email, body.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AuthResponse(access_token=token, user={"id": str(user.id), "email": user.email})


@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    if get_settings().auth_disabled:
        raise HTTPException(status_code=403, detail="auth disabled in local mode")
    try:
        user, token = await auth.login(body.email, body.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return AuthResponse(access_token=token, user={"id": str(user.id), "email": user.email})

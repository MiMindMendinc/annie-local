from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, EmailStr, Field


class ChatRequest(BaseModel):
    message: Annotated[str, Field(min_length=1, max_length=20_000)]


class MemorySearchRequest(BaseModel):
    query: str = ""
    limit: int = Field(default=10, ge=1, le=100)


class SettingsUpdate(BaseModel):
    model: str | None = Field(default=None, min_length=1, max_length=128)
    ollama_url: str | None = Field(default=None, min_length=8, max_length=512)
    voice_url: str | None = Field(default=None, min_length=8, max_length=512)
    temperature: float | None = Field(default=None, ge=0, le=2)
    tools_enabled: bool | None = None
    system_prompt: str | None = Field(default=None, min_length=1, max_length=50_000)


class SpeakRequest(BaseModel):
    text: Annotated[str, Field(min_length=1, max_length=2_000)]


class KnowledgeDeleteRequest(BaseModel):
    kind: str
    item_id: str | None = None


class RegisterRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=8, max_length=128)]


class LoginRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=8, max_length=128)]


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]

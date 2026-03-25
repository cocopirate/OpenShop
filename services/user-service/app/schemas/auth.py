from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uid: str  # public_id (UUID v7) as string
    username: str
    roles: list[str]
    permissions: list[str]
    status: str
    ver: int
    exp: int | None = None

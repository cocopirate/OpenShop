from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AdminUserCreate(BaseModel):
    username: str
    password: str
    status: str = "active"


class AdminUserUpdate(BaseModel):
    username: Optional[str] = None
    status: Optional[str] = None


class AdminUserStatusUpdate(BaseModel):
    status: str  # "active" or "disabled"


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: UUID
    username: str
    status: str
    created_at: datetime

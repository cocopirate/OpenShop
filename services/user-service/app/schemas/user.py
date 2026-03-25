from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    username: str
    password: str
    status: str = "active"


class UserUpdate(BaseModel):
    username: Optional[str] = None
    status: Optional[str] = None


class UserStatusUpdate(BaseModel):
    status: str  # "active" or "disabled"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    status: str
    created_at: datetime

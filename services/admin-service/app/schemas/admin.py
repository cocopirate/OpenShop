from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AdminAccountCreate(BaseModel):
    username: str
    password: str
    real_name: Optional[str] = None
    phone: Optional[str] = None
    status: int = 1
    created_by: Optional[int] = None


class AdminAccountUpdate(BaseModel):
    username: Optional[str] = None
    real_name: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[int] = None


class AdminAccountStatusUpdate(BaseModel):
    status: int  # 1=active, 0=disabled


class AdminAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: UUID
    username: str
    real_name: Optional[str] = None
    phone: Optional[str] = None
    status: int
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime

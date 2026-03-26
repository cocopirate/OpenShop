from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SubAccountCreate(BaseModel):
    username: str
    real_name: Optional[str] = None
    phone: Optional[str] = None
    created_by: Optional[int] = None


class SubAccountUpdate(BaseModel):
    real_name: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[int] = None


class SubAccountResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    merchant_id: int
    username: str
    real_name: Optional[str] = None
    phone: Optional[str] = None
    status: int
    created_at: datetime


class RoleAssignRequest(BaseModel):
    role_ids: list[int]

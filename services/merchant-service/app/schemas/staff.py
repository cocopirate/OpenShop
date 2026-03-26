from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class StaffCreate(BaseModel):
    store_id: Optional[int] = None
    real_name: str
    phone: Optional[str] = None
    job_type: Optional[int] = None


class StaffUpdate(BaseModel):
    store_id: Optional[int] = None
    real_name: Optional[str] = None
    phone: Optional[str] = None
    job_type: Optional[int] = None
    status: Optional[int] = None


class StaffResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    merchant_id: int
    store_id: Optional[int] = None
    real_name: str
    phone: Optional[str] = None
    job_type: Optional[int] = None
    status: int
    created_at: datetime


class RoleAssignRequest(BaseModel):
    role_ids: list[int]

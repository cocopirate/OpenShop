from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PermissionCreate(BaseModel):
    code: str
    name: str
    type: str  # "menu" or "api"
    method: Optional[str] = None
    path: Optional[str] = None
    parent_id: Optional[int] = None


class PermissionUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    parent_id: Optional[int] = None


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    type: str
    method: Optional[str] = None
    path: Optional[str] = None
    parent_id: Optional[int] = None
    created_at: datetime

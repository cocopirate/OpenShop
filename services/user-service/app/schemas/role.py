from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RoleCreate(BaseModel):
    name: str
    desc: Optional[str] = None


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    desc: Optional[str] = None


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    desc: Optional[str] = None
    created_at: datetime

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class AdminRoleCreate(BaseModel):
    role_code: str
    role_name: str
    is_system: int = 0
    status: int = 1


class AdminRoleUpdate(BaseModel):
    role_code: Optional[str] = None
    role_name: Optional[str] = None
    status: Optional[int] = None


class AdminRoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role_code: str
    role_name: str
    is_system: int
    status: int

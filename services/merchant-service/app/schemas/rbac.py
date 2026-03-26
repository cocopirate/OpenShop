from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class RoleCreate(BaseModel):
    role_code: str
    role_name: Optional[str] = None
    is_system: int = 0


class RoleUpdate(BaseModel):
    role_name: Optional[str] = None


class RoleResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    merchant_id: int
    role_code: str
    role_name: Optional[str] = None
    is_system: int


class PermissionResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    perm_code: str
    perm_name: Optional[str] = None
    perm_type: Optional[int] = None


class PermissionAssignRequest(BaseModel):
    permission_ids: list[int]

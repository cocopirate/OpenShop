from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class AdminPermissionCreate(BaseModel):
    parent_id: int = 0
    perm_code: str
    perm_name: str
    perm_type: Optional[int] = None  # 1=menu 2=button 3=api
    path: Optional[str] = None
    method: Optional[str] = None


class AdminPermissionUpdate(BaseModel):
    parent_id: Optional[int] = None
    perm_code: Optional[str] = None
    perm_name: Optional[str] = None
    perm_type: Optional[int] = None
    path: Optional[str] = None
    method: Optional[str] = None


class AdminPermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_id: int
    perm_code: str
    perm_name: str
    perm_type: Optional[int] = None
    path: Optional[str] = None
    method: Optional[str] = None
    children: List["AdminPermissionResponse"] = []


AdminPermissionResponse.model_rebuild()

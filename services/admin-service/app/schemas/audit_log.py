from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AuditLogCreate(BaseModel):
    admin_id: int
    admin_name: Optional[str] = None
    action: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    request_body: Optional[str] = None
    ip: Optional[str] = None


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    admin_id: int
    admin_name: Optional[str] = None
    action: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    request_body: Optional[str] = None
    ip: Optional[str] = None
    created_at: datetime

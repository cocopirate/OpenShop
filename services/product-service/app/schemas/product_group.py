"""Pydantic schemas for ProductGroup."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.product_group import GroupStatus, GroupType


class ProductGroupCreate(BaseModel):
    name: str
    type: GroupType = GroupType.MANUAL
    status: GroupStatus = GroupStatus.ENABLE


class ProductGroupUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[GroupStatus] = None


class ProductGroupResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    type: GroupType
    status: GroupStatus
    created_at: datetime


class GroupItemCreate(BaseModel):
    spu_id: int
    sort_order: int = 0


class GroupItemBatchCreate(BaseModel):
    items: list[GroupItemCreate]


class GroupItemResponse(BaseModel):
    model_config = {"from_attributes": True}

    group_id: int
    spu_id: int
    sort_order: int

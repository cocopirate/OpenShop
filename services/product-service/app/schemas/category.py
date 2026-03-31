"""Pydantic schemas for Category."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.category import CategoryStatus


class CategoryCreate(BaseModel):
    parent_id: int = 0
    name: str
    sort_order: int = 0
    status: CategoryStatus = CategoryStatus.ENABLE


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None
    status: Optional[CategoryStatus] = None


class CategoryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    parent_id: int
    name: str
    level: int
    path: str
    sort_order: int
    status: CategoryStatus
    created_at: datetime
    updated_at: datetime


class CategoryTreeNode(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    parent_id: int
    name: str
    level: int
    path: str
    sort_order: int
    status: CategoryStatus
    children: list[CategoryTreeNode] = []

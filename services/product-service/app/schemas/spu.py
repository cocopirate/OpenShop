"""Pydantic schemas for SPU."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.spu import SpuStatus


class SpuCreate(BaseModel):
    name: str
    category_id: int
    brand_id: Optional[int] = None
    description: Optional[str] = None
    status: SpuStatus = SpuStatus.DRAFT


class SpuUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    description: Optional[str] = None


class SpuResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    category_id: int
    brand_id: Optional[int] = None
    description: Optional[str] = None
    status: SpuStatus
    created_at: datetime
    updated_at: datetime


class SpuListResponse(BaseModel):
    items: list[SpuResponse]
    total: int
    page: int
    size: int

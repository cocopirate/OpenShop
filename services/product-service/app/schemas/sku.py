"""Pydantic schemas for SKU."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel

from app.models.sku import SkuStatus


class SkuCreate(BaseModel):
    spu_id: int
    title: str
    attributes: Optional[dict[str, Any]] = None
    price: Decimal
    status: SkuStatus = SkuStatus.ENABLE


class SkuBatchCreate(BaseModel):
    items: list[SkuCreate]


class SkuUpdate(BaseModel):
    title: Optional[str] = None
    attributes: Optional[dict[str, Any]] = None
    price: Optional[Decimal] = None
    status: Optional[SkuStatus] = None


class SkuResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    spu_id: int
    title: str
    attributes: Optional[dict[str, Any]] = None
    price: Decimal
    status: SkuStatus
    created_at: datetime
    updated_at: datetime

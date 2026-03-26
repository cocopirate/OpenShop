from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class StoreCreate(BaseModel):
    store_name: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[Decimal] = None
    lng: Optional[Decimal] = None


class StoreUpdate(BaseModel):
    store_name: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[Decimal] = None
    lng: Optional[Decimal] = None
    status: Optional[int] = None


class StoreResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    merchant_id: int
    store_name: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[Decimal] = None
    lng: Optional[Decimal] = None
    status: int
    created_at: datetime

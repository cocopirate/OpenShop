from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class MerchantCreate(BaseModel):
    merchant_name: str
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    business_license: Optional[str] = None
    category_id: Optional[int] = None


class MerchantUpdate(BaseModel):
    merchant_name: Optional[str] = None
    contact_name: Optional[str] = None
    business_license: Optional[str] = None
    category_id: Optional[int] = None


class MerchantStatusUpdate(BaseModel):
    status: int


class MerchantResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    public_id: UUID
    merchant_name: str
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    business_license: Optional[str] = None
    category_id: Optional[int] = None
    status: int
    verified_at: Optional[datetime] = None
    created_at: datetime

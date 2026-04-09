"""Pydantic v2 schemas for lead order management."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


# --------------------------------------------------------------------------- #
# Request schemas                                                               #
# --------------------------------------------------------------------------- #


class LeadCreate(BaseModel):
    phone: str
    city: str
    district: str
    product_ids: list[str]
    remark: Optional[str] = None
    source: str
    consumer_id: Optional[UUID] = None

    @field_validator("phone")
    @classmethod
    def phone_must_be_valid(cls, v: str) -> str:
        if not re.match(r"^\d{7,20}$", v):
            raise ValueError("Invalid phone number format")
        return v

    @field_validator("source")
    @classmethod
    def source_must_be_valid(cls, v: str) -> str:
        allowed = {"app", "miniprogram", "h5"}
        if v not in allowed:
            raise ValueError(f"source must be one of {allowed}")
        return v

    @field_validator("product_ids")
    @classmethod
    def product_ids_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("product_ids must not be empty")
        return v


class LeadConvert(BaseModel):
    converted_order_id: Optional[UUID] = None
    note: Optional[str] = None


class LeadCancel(BaseModel):
    note: Optional[str] = None


# --------------------------------------------------------------------------- #
# Response schemas                                                              #
# --------------------------------------------------------------------------- #


class LeadCreateResponse(BaseModel):
    id: UUID
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LeadResponse(BaseModel):
    id: UUID
    phone: str
    city: str
    district: str
    product_ids: list[str]
    remark: Optional[str] = None
    status: str
    source: str
    consumer_id: Optional[UUID] = None
    merchant_id: Optional[UUID] = None
    converted_order_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadListResponse(BaseModel):
    id: UUID
    phone: str
    city: str
    district: str
    product_ids: list[str]
    status: str
    source: str
    consumer_id: Optional[UUID] = None
    merchant_id: Optional[UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @staticmethod
    def mask_phone(phone: str) -> str:
        """Mask phone number: 13800138000 → 138****0000."""
        if len(phone) >= 7:
            return phone[:3] + "****" + phone[-4:]
        return "****"


class LeadStatusLogResponse(BaseModel):
    id: UUID
    lead_id: UUID
    from_status: str
    to_status: str
    operator_id: Optional[UUID] = None
    operator_type: str
    note: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

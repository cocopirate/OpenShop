"""Pydantic schemas for consumer account and address management."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ConsumerCreate(BaseModel):
    nickname: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None


class ConsumerUpdate(BaseModel):
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    gender: Optional[int] = None
    birthday: Optional[date] = None


class ConsumerResponse(BaseModel):
    public_id: UUID
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[int] = None
    birthday: Optional[date] = None
    points: int
    level: int
    status: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AddressCreate(BaseModel):
    receiver: Optional[str] = None
    phone: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    detail: Optional[str] = None
    is_default: int = 0


class AddressUpdate(BaseModel):
    receiver: Optional[str] = None
    phone: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    detail: Optional[str] = None
    is_default: Optional[int] = None


class AddressResponse(BaseModel):
    id: int
    consumer_id: int
    receiver: Optional[str] = None
    phone: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    detail: Optional[str] = None
    is_default: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PointsAdjustRequest(BaseModel):
    delta: int
    reason: str
    ref_id: str

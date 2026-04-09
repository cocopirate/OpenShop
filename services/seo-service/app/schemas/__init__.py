from datetime import datetime
from typing import Any

from pydantic import BaseModel


# ─── City ────────────────────────────────────────────────────────────────────

class CityCreate(BaseModel):
    slug: str
    name: str
    pinyin: str | None = None
    is_active: bool = True


class CityUpdate(BaseModel):
    name: str | None = None
    pinyin: str | None = None
    is_active: bool | None = None


class CityOut(BaseModel):
    id: int
    slug: str
    name: str
    pinyin: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── District ────────────────────────────────────────────────────────────────

class DistrictCreate(BaseModel):
    city_id: int
    slug: str
    name: str
    landmarks: list[str] = []
    is_active: bool = True


class DistrictUpdate(BaseModel):
    name: str | None = None
    landmarks: list[str] | None = None
    is_active: bool | None = None


class DistrictOut(BaseModel):
    id: int
    city_id: int
    slug: str
    name: str
    landmarks: list[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Service ─────────────────────────────────────────────────────────────────

class ServiceCreate(BaseModel):
    slug: str
    name: str
    keywords: list[str] = []
    base_price: int | None = None
    description: str | None = None
    is_active: bool = True


class ServiceUpdate(BaseModel):
    name: str | None = None
    keywords: list[str] | None = None
    base_price: int | None = None
    description: str | None = None
    is_active: bool | None = None


class ServiceOut(BaseModel):
    id: int
    slug: str
    name: str
    keywords: list[str]
    base_price: int | None
    description: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── SEO Page ────────────────────────────────────────────────────────────────

class SeoPageOut(BaseModel):
    id: int
    city_id: int
    district_id: int
    service_id: int
    slug: str
    title: str | None
    meta_description: str | None
    h1: str | None
    content: Any | None
    status: str
    generation_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SeoPageUpdate(BaseModel):
    status: str | None = None
    title: str | None = None
    meta_description: str | None = None
    h1: str | None = None


class SeoPageListResponse(BaseModel):
    items: list[SeoPageOut]
    total: int
    page: int
    page_size: int


# ─── Generation ──────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    city_slug: str
    district_slug: str
    service_slug: str
    force: bool = False


class GenerateBatchRequest(BaseModel):
    city_slugs: list[str] = []
    force: bool = False


class JobResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    type: str
    status: str
    result: dict | None = None
    error_log: list = []

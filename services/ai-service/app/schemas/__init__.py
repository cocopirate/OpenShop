"""Pydantic schemas for AI Service request/response."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

class UsageInfo(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class CompletionResponse(BaseModel):
    call_id: uuid.UUID
    content: Any
    usage: UsageInfo
    provider: str
    model: str
    cache_hit: bool
    duration_ms: int


# ---------------------------------------------------------------------------
# /complete/raw
# ---------------------------------------------------------------------------

class RawCompleteRequest(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    system_prompt: str
    user_prompt: str
    temperature: float = 0.7
    max_tokens: int = 1000
    response_format: str = "text"
    caller_service: str
    caller_ref_id: str | None = None
    cache_ttl_seconds: int = 3600


# ---------------------------------------------------------------------------
# /complete/template
# ---------------------------------------------------------------------------

class TemplateCompleteRequest(BaseModel):
    template_key: str
    variables: dict[str, str] = Field(default_factory=dict)
    caller_service: str
    caller_ref_id: str | None = None
    cache_ttl_seconds: int = 3600


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

class TemplateCreate(BaseModel):
    key: str
    provider: str = "openai"
    model: str | None = None
    system_prompt: str
    user_prompt_template: str
    temperature: float = 0.7
    max_tokens: int = 1000
    response_format: str = "text"


class TemplateUpdate(BaseModel):
    temperature: float | None = None
    max_tokens: int | None = None
    response_format: str | None = None
    model: str | None = None


class TemplateResponse(BaseModel):
    id: int
    key: str
    version: int
    is_active: bool
    provider: str
    model: str | None
    system_prompt: str
    user_prompt_template: str
    temperature: float
    max_tokens: int
    response_format: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Call logs
# ---------------------------------------------------------------------------

class CallLogResponse(BaseModel):
    id: uuid.UUID
    caller_service: str
    caller_ref_id: str | None
    template_key: str | None
    template_version: int | None
    provider: str
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    estimated_cost_usd: float | None
    status: str | None
    error_message: str | None
    duration_ms: int | None
    request_hash: str | None
    cache_hit: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CallLogListResponse(BaseModel):
    items: list[CallLogResponse]
    total: int
    page: int
    page_size: int


class ServiceStats(BaseModel):
    caller_service: str
    total_calls: int
    success_rate: float
    total_tokens: int
    estimated_cost_usd: float
    avg_duration_ms: float


class TemplateStats(BaseModel):
    template_key: str
    total_calls: int
    cache_hit_rate: float


class LogStatsResponse(BaseModel):
    period: str
    by_service: list[ServiceStats]
    by_template: list[TemplateStats]

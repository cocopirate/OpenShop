"""Core completion endpoints: /complete/raw and /complete/template."""
from __future__ import annotations

import json
import time
import uuid

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models.call_log import CallLog
from app.models.prompt_template import PromptTemplate
from app.schemas import (
    CompletionResponse,
    RawCompleteRequest,
    TemplateCompleteRequest,
    UsageInfo,
)
from app.services.cache import ResultCache, make_request_hash
from app.services.providers.openai import estimate_cost
from app.services.rate_limiter import RateLimiter
from app.services.router import get_provider

log = structlog.get_logger(__name__)

router = APIRouter()


def _get_redis(request: Request) -> aioredis.Redis:
    return request.app.state.redis


async def _run_completion(
    *,
    provider_name: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    response_format: str,
    caller_service: str,
    caller_ref_id: str | None,
    template_key: str | None,
    template_version: int | None,
    cache_ttl_seconds: int,
    db: AsyncSession,
    redis: aioredis.Redis,
) -> CompletionResponse:
    request_hash = make_request_hash(system_prompt, user_prompt)

    # Rate limit check (RPM only pre-call; TPM checked post-call against 0 estimate)
    rate_limiter = RateLimiter(redis)
    allowed, retry_after = await rate_limiter.check_and_increment(caller_service)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={"error": "rate_limited", "retry_after": retry_after},
        )

    # Cache lookup
    result_cache = ResultCache(redis)
    cache_hit = False
    content_str: str | None = None

    if cache_ttl_seconds != 0:
        content_str = await result_cache.get(request_hash)
        if content_str is not None:
            cache_hit = True

    call_id = uuid.uuid4()
    start_ms = int(time.time() * 1000)

    if cache_hit and content_str is not None:
        duration_ms = int(time.time() * 1000) - start_ms
        log_entry = CallLog(
            id=call_id,
            caller_service=caller_service,
            caller_ref_id=caller_ref_id,
            template_key=template_key,
            template_version=template_version,
            provider=provider_name,
            model=model,
            status="success",
            duration_ms=duration_ms,
            request_hash=request_hash,
            cache_hit=True,
        )
        db.add(log_entry)
        await db.flush()

        content = _parse_content(content_str, response_format)
        return CompletionResponse(
            call_id=call_id,
            content=content,
            usage=UsageInfo(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            provider=provider_name,
            model=model,
            cache_hit=True,
            duration_ms=duration_ms,
        )

    # Actual AI call
    provider = get_provider(provider_name)
    status = "success"
    error_message: str | None = None
    result = None

    try:
        result = await provider.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
    except Exception as exc:
        status = "failed"
        error_message = str(exc)
        log.error("complete.provider_error", error=error_message)

    duration_ms = int(time.time() * 1000) - start_ms

    prompt_tokens = result.prompt_tokens if result else 0
    completion_tokens = result.completion_tokens if result else 0
    total_tokens = result.total_tokens if result else 0
    actual_model = result.model if result else model
    cost = estimate_cost(prompt_tokens, completion_tokens) if result else 0.0

    # TPM rate limit post-check
    if result and total_tokens > 0:
        tpm_allowed, tpm_retry = await rate_limiter.check_and_increment(
            caller_service, token_count=total_tokens
        )
        if not tpm_allowed:
            status = "rate_limited"

    log_entry = CallLog(
        id=call_id,
        caller_service=caller_service,
        caller_ref_id=caller_ref_id,
        template_key=template_key,
        template_version=template_version,
        provider=provider_name,
        model=actual_model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=cost,
        status=status,
        error_message=error_message,
        duration_ms=duration_ms,
        request_hash=request_hash,
        cache_hit=False,
    )
    db.add(log_entry)
    await db.flush()

    if status == "failed":
        raise HTTPException(status_code=502, detail=error_message or "AI provider error")

    content_str = result.content  # type: ignore[union-attr]

    # Store in cache
    if cache_ttl_seconds != 0 and content_str:
        await result_cache.set(request_hash, content_str, ttl=cache_ttl_seconds)

    content = _parse_content(content_str, response_format)
    return CompletionResponse(
        call_id=call_id,
        content=content,
        usage=UsageInfo(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        ),
        provider=provider_name,
        model=actual_model,
        cache_hit=False,
        duration_ms=duration_ms,
    )


def _parse_content(content_str: str, response_format: str):
    if response_format == "json_object":
        try:
            return json.loads(content_str)
        except json.JSONDecodeError:
            return content_str
    return content_str


@router.post("/raw", response_model=CompletionResponse)
async def complete_raw(
    body: RawCompleteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    redis = _get_redis(request)
    return await _run_completion(
        provider_name=body.provider,
        model=body.model,
        system_prompt=body.system_prompt,
        user_prompt=body.user_prompt,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
        response_format=body.response_format,
        caller_service=body.caller_service,
        caller_ref_id=body.caller_ref_id,
        template_key=None,
        template_version=None,
        cache_ttl_seconds=body.cache_ttl_seconds,
        db=db,
        redis=redis,
    )


@router.post("/template", response_model=CompletionResponse)
async def complete_template(
    body: TemplateCompleteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # Look up active template
    result = await db.execute(
        select(PromptTemplate).where(
            PromptTemplate.key == body.template_key,
            PromptTemplate.is_active.is_(True),
        )
    )
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail=f"No active template for key: {body.template_key}")

    # Render user prompt template
    try:
        user_prompt = str(template.user_prompt_template).format(**body.variables)
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=f"Missing template variable: {exc}")

    model = str(template.model or settings.OPENAI_DEFAULT_MODEL)
    redis = _get_redis(request)

    return await _run_completion(
        provider_name=str(template.provider),
        model=model,
        system_prompt=str(template.system_prompt),
        user_prompt=user_prompt,
        temperature=float(template.temperature),
        max_tokens=int(template.max_tokens),
        response_format=str(template.response_format),
        caller_service=body.caller_service,
        caller_ref_id=body.caller_ref_id,
        template_key=body.template_key,
        template_version=int(template.version),
        cache_ttl_seconds=body.cache_ttl_seconds,
        db=db,
        redis=redis,
    )

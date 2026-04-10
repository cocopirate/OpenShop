"""Prompt template management endpoints."""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import TEMPLATE_EXISTS, TEMPLATE_NOT_FOUND, error_response, ok
from app.database import get_db
from app.models.prompt_template import PromptTemplate
from app.schemas import TemplateCreate, TemplateResponse, TemplateUpdate

log = structlog.get_logger(__name__)

router = APIRouter()


@router.get("")
async def list_templates(
    key: str | None = Query(default=None, description="Filter by key (partial match)"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    stmt = select(PromptTemplate)
    if key:
        stmt = stmt.where(PromptTemplate.key.contains(key))
    result = await db.execute(stmt.order_by(PromptTemplate.key, PromptTemplate.version.desc()))
    items = [TemplateResponse.model_validate(t).model_dump() for t in result.scalars().all()]
    return JSONResponse(content=ok(items))


@router.get("/{key}")
async def get_active_template(key: str, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    result = await db.execute(
        select(PromptTemplate).where(
            PromptTemplate.key == key,
            PromptTemplate.is_active.is_(True),
        )
    )
    template = result.scalar_one_or_none()
    if template is None:
        return error_response(404, TEMPLATE_NOT_FOUND, f"No active template for key: {key}")
    return JSONResponse(content=ok(TemplateResponse.model_validate(template).model_dump()))


@router.get("/{key}/versions")
async def list_template_versions(key: str, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    result = await db.execute(
        select(PromptTemplate)
        .where(PromptTemplate.key == key)
        .order_by(PromptTemplate.version.desc())
    )
    templates = result.scalars().all()
    if not templates:
        return error_response(404, TEMPLATE_NOT_FOUND, f"No templates found for key: {key}")
    items = [TemplateResponse.model_validate(t).model_dump() for t in templates]
    return JSONResponse(content=ok(items))


@router.post("", status_code=201)
async def create_template(body: TemplateCreate, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    # Check if key already exists
    existing = await db.execute(
        select(PromptTemplate).where(PromptTemplate.key == body.key).limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        return error_response(
            409,
            TEMPLATE_EXISTS,
            f"Template key '{body.key}' already exists. Use POST /templates/{{key}}/versions to add a new version.",
        )

    template = PromptTemplate(
        key=body.key,
        version=1,
        is_active=True,
        provider=body.provider,
        model=body.model,
        system_prompt=body.system_prompt,
        user_prompt_template=body.user_prompt_template,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
        response_format=body.response_format,
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return JSONResponse(status_code=201, content=ok(TemplateResponse.model_validate(template).model_dump()))


@router.post("/{key}/versions", status_code=201)
async def add_template_version(key: str, body: TemplateCreate, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    # Get current latest version
    result = await db.execute(
        select(PromptTemplate)
        .where(PromptTemplate.key == key)
        .order_by(PromptTemplate.version.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    if latest is None:
        return error_response(404, TEMPLATE_NOT_FOUND, f"No templates found for key: {key}")

    # Deactivate current active version
    active_result = await db.execute(
        select(PromptTemplate).where(
            PromptTemplate.key == key,
            PromptTemplate.is_active.is_(True),
        )
    )
    active = active_result.scalar_one_or_none()
    if active:
        active.is_active = False

    new_version = latest.version + 1
    template = PromptTemplate(
        key=key,
        version=new_version,
        is_active=True,
        provider=body.provider,
        model=body.model,
        system_prompt=body.system_prompt,
        user_prompt_template=body.user_prompt_template,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
        response_format=body.response_format,
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return JSONResponse(status_code=201, content=ok(TemplateResponse.model_validate(template).model_dump()))


@router.patch("/{key}")
async def patch_template(key: str, body: TemplateUpdate, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    result = await db.execute(
        select(PromptTemplate).where(
            PromptTemplate.key == key,
            PromptTemplate.is_active.is_(True),
        )
    )
    template = result.scalar_one_or_none()
    if template is None:
        return error_response(404, TEMPLATE_NOT_FOUND, f"No active template for key: {key}")

    if body.temperature is not None:
        template.temperature = body.temperature
    if body.max_tokens is not None:
        template.max_tokens = body.max_tokens
    if body.response_format is not None:
        template.response_format = body.response_format
    if body.model is not None:
        template.model = body.model

    await db.flush()
    await db.refresh(template)
    return JSONResponse(content=ok(TemplateResponse.model_validate(template).model_dump()))


@router.post("/{key}/rollback/{version}")
async def rollback_template(key: str, version: int, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    # Find target version
    result = await db.execute(
        select(PromptTemplate).where(
            PromptTemplate.key == key,
            PromptTemplate.version == version,
        )
    )
    target = result.scalar_one_or_none()
    if target is None:
        return error_response(404, TEMPLATE_NOT_FOUND, f"Version {version} not found for key: {key}")

    # Deactivate current active
    active_result = await db.execute(
        select(PromptTemplate).where(
            PromptTemplate.key == key,
            PromptTemplate.is_active.is_(True),
        )
    )
    active = active_result.scalar_one_or_none()
    if active and active.id != target.id:
        active.is_active = False

    target.is_active = True
    await db.flush()
    await db.refresh(target)
    return JSONResponse(content=ok(TemplateResponse.model_validate(target).model_dump()))


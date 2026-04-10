"""Prompt template management endpoints."""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.prompt_template import PromptTemplate
from app.schemas import TemplateCreate, TemplateResponse, TemplateUpdate

log = structlog.get_logger(__name__)

router = APIRouter()


@router.get("", response_model=list[TemplateResponse])
async def list_templates(
    key: str | None = Query(default=None, description="Filter by key (partial match)"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PromptTemplate)
    if key:
        stmt = stmt.where(PromptTemplate.key.contains(key))
    result = await db.execute(stmt.order_by(PromptTemplate.key, PromptTemplate.version.desc()))
    return result.scalars().all()


@router.get("/{key}", response_model=TemplateResponse)
async def get_active_template(key: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PromptTemplate).where(
            PromptTemplate.key == key,
            PromptTemplate.is_active.is_(True),
        )
    )
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail=f"No active template for key: {key}")
    return template


@router.get("/{key}/versions", response_model=list[TemplateResponse])
async def list_template_versions(key: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PromptTemplate)
        .where(PromptTemplate.key == key)
        .order_by(PromptTemplate.version.desc())
    )
    templates = result.scalars().all()
    if not templates:
        raise HTTPException(status_code=404, detail=f"No templates found for key: {key}")
    return templates


@router.post("", response_model=TemplateResponse, status_code=201)
async def create_template(body: TemplateCreate, db: AsyncSession = Depends(get_db)):
    # Check if key already exists
    existing = await db.execute(
        select(PromptTemplate).where(PromptTemplate.key == body.key).limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Template key '{body.key}' already exists. Use POST /templates/{{key}}/versions to add a new version.",
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
    return template


@router.post("/{key}/versions", response_model=TemplateResponse, status_code=201)
async def add_template_version(key: str, body: TemplateCreate, db: AsyncSession = Depends(get_db)):
    # Get current active version
    result = await db.execute(
        select(PromptTemplate)
        .where(PromptTemplate.key == key)
        .order_by(PromptTemplate.version.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    if latest is None:
        raise HTTPException(status_code=404, detail=f"No templates found for key: {key}")

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
    return template


@router.patch("/{key}", response_model=TemplateResponse)
async def patch_template(key: str, body: TemplateUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PromptTemplate).where(
            PromptTemplate.key == key,
            PromptTemplate.is_active.is_(True),
        )
    )
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail=f"No active template for key: {key}")

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
    return template


@router.post("/{key}/rollback/{version}", response_model=TemplateResponse)
async def rollback_template(key: str, version: int, db: AsyncSession = Depends(get_db)):
    # Find target version
    result = await db.execute(
        select(PromptTemplate).where(
            PromptTemplate.key == key,
            PromptTemplate.version == version,
        )
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail=f"Version {version} not found for key: {key}")

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
    return target

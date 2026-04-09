"""Generation trigger router."""
from __future__ import annotations

import uuid

import structlog
from arq.connections import ArqRedis, RedisSettings, create_pool
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.city import City
from app.models.district import District
from app.models.generation_job import GenerationJob
from app.models.seo_page import SeoPage
from app.models.service import Service
from app.schemas import GenerateBatchRequest, GenerateRequest, JobResponse, JobStatusResponse

log = structlog.get_logger(__name__)
router = APIRouter()


async def get_redis_pool() -> ArqRedis:
    return await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))


@router.post("", response_model=JobResponse, status_code=202)
async def trigger_generate(
    payload: GenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    # Validate city
    city_result = await db.execute(select(City).where(City.slug == payload.city_slug))
    city = city_result.scalar_one_or_none()
    if not city:
        raise HTTPException(status_code=404, detail=f"city_slug not found: {payload.city_slug}")

    # Validate district
    district_result = await db.execute(
        select(District).where(
            District.slug == payload.district_slug,
            District.city_id == city.id,
        )
    )
    district = district_result.scalar_one_or_none()
    if not district:
        raise HTTPException(
            status_code=404,
            detail=f"district_slug not found: {payload.district_slug}",
        )

    # Validate service
    service_result = await db.execute(select(Service).where(Service.slug == payload.service_slug))
    service = service_result.scalar_one_or_none()
    if not service:
        raise HTTPException(
            status_code=404, detail=f"service_slug not found: {payload.service_slug}"
        )

    # Build slug
    page_slug = f"{city.pinyin or city.slug}/{district.slug}/{service.slug}"

    # Check existing page if not forcing
    if not payload.force:
        existing_result = await db.execute(select(SeoPage).where(SeoPage.slug == page_slug))
        existing = existing_result.scalar_one_or_none()
        if existing:
            return JobResponse(job_id=str(existing.id), status="exists")

    # Create GenerationJob record
    job_id = uuid.uuid4()
    job = GenerationJob(
        id=job_id,
        type="single",
        status="pending",
        payload={
            "city_slug": payload.city_slug,
            "district_slug": payload.district_slug,
            "service_slug": payload.service_slug,
            "force": payload.force,
        },
    )
    db.add(job)
    await db.commit()

    # Enqueue ARQ task
    try:
        redis = await get_redis_pool()
        await redis.enqueue_job(
            "generate_single_page",
            job_id=str(job_id),
            city_slug=payload.city_slug,
            district_slug=payload.district_slug,
            service_slug=payload.service_slug,
            force=payload.force,
        )
        await redis.aclose()
    except Exception as exc:
        log.error("generate.enqueue_failed", job_id=str(job_id), error=str(exc))
        raise HTTPException(status_code=503, detail="Redis unavailable")

    return JobResponse(job_id=str(job_id), status="pending")


@router.post("/batch", response_model=JobResponse, status_code=202)
async def trigger_batch_generate(
    payload: GenerateBatchRequest,
    db: AsyncSession = Depends(get_db),
):
    job_id = uuid.uuid4()
    job = GenerationJob(
        id=job_id,
        type="batch",
        status="pending",
        payload={
            "city_slugs": payload.city_slugs,
            "force": payload.force,
        },
    )
    db.add(job)
    await db.commit()

    try:
        redis = await get_redis_pool()
        await redis.enqueue_job(
            "generate_batch_pages",
            job_id=str(job_id),
            city_slugs=payload.city_slugs,
            force=payload.force,
        )
        await redis.aclose()
    except Exception as exc:
        log.error("generate.batch_enqueue_failed", job_id=str(job_id), error=str(exc))
        raise HTTPException(status_code=503, detail="Redis unavailable")

    return JobResponse(job_id=str(job_id), status="pending")


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid job_id format")

    job = await db.get(GenerationJob, job_uuid)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return JobStatusResponse(
        job_id=str(job.id),
        type=job.type,
        status=job.status,
        result=job.result,
        error_log=job.error_log or [],
    )

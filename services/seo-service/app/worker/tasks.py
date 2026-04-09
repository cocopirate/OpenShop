"""ARQ async worker tasks for SEO content generation."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from arq import ArqRedis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.city import City
from app.models.district import District
from app.models.generation_job import GenerationJob
from app.models.seo_page import SeoPage
from app.models.service import Service
from app.services.ai_generator import generate_seo_content
from app.services.duplicate import is_duplicate

log = structlog.get_logger(__name__)


def _make_session_factory():
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def _get_existing_service_contents(
    session: AsyncSession, service_id: int, exclude_slug: str | None = None
) -> list[dict]:
    """Fetch existing content for same service type (for duplicate detection)."""
    stmt = select(SeoPage.content).where(
        SeoPage.service_id == service_id,
        SeoPage.content.isnot(None),
    )
    if exclude_slug:
        stmt = stmt.where(SeoPage.slug != exclude_slug)
    result = await session.execute(stmt)
    return [row[0] for row in result.fetchall() if row[0]]


async def generate_single_page(
    ctx: dict,
    job_id: str,
    city_slug: str,
    district_slug: str,
    service_slug: str,
    force: bool = False,
) -> None:
    """ARQ task: generate a single SEO page."""
    session_factory = _make_session_factory()

    async with session_factory() as session:
        # Update job status to running
        job = await session.get(GenerationJob, uuid.UUID(job_id))
        if not job:
            log.error("worker.job_not_found", job_id=job_id)
            return
        job.status = "running"
        await session.commit()

        # Fetch city, district, service
        city_row = await session.execute(select(City).where(City.slug == city_slug))
        city = city_row.scalar_one_or_none()

        district_row = await session.execute(
            select(District).where(
                District.slug == district_slug,
                District.city_id == city.id if city else False,
            )
        )
        district = district_row.scalar_one_or_none()

        service_row = await session.execute(select(Service).where(Service.slug == service_slug))
        service = service_row.scalar_one_or_none()

        if not city or not district or not service:
            missing = []
            if not city:
                missing.append(f"city_slug={city_slug}")
            if not district:
                missing.append(f"district_slug={district_slug}")
            if not service:
                missing.append(f"service_slug={service_slug}")
            job.status = "failed"
            job.error_log = [{"error": f"Not found: {', '.join(missing)}"}]
            job.result = {"total": 1, "created": 0, "skipped": 0, "failed": 1}
            job.finished_at = datetime.now(timezone.utc)
            await session.commit()
            return

        page_slug = f"{city.pinyin or city.slug}/{district.slug}/{service.slug}"
        result = {"total": 1, "created": 0, "skipped": 0, "failed": 0}
        error_log = []

        # Check existing
        existing_row = await session.execute(select(SeoPage).where(SeoPage.slug == page_slug))
        existing_page = existing_row.scalar_one_or_none()

        if existing_page and not force:
            result["skipped"] = 1
            job.status = "done"
            job.result = result
            job.finished_at = datetime.now(timezone.utc)
            await session.commit()
            return

        # Generate content with retry
        content = None
        retries = 0
        max_retries = settings.MAX_RETRIES
        existing_contents = await _get_existing_service_contents(
            session, service.id, exclude_slug=page_slug
        )

        while retries <= max_retries:
            try:
                generated = await generate_seo_content(
                    city_name=city.name,
                    district_name=district.name,
                    service_name=service.name,
                    service_description=service.description or "",
                    base_price=service.base_price,
                    landmarks=district.landmarks or [],
                    keywords=service.keywords or [],
                )
                if is_duplicate(generated, existing_contents):
                    retries += 1
                    log.warning("worker.duplicate_detected", slug=page_slug, retry=retries)
                    if retries > max_retries:
                        content = generated
                        # Mark as needs_review
                        break
                    continue
                content = generated
                break
            except Exception as exc:
                log.error("worker.ai_error", slug=page_slug, error=str(exc))
                retries += 1
                if retries > max_retries:
                    error_log.append({"slug": page_slug, "error": str(exc)})
                    result["failed"] = 1
                    job.status = "done"
                    job.result = result
                    job.error_log = error_log
                    job.finished_at = datetime.now(timezone.utc)
                    await session.commit()
                    return

        page_status = "draft"
        if retries > max_retries and content is None:
            page_status = "needs_review"
            error_log.append({"slug": page_slug, "error": "max retries exceeded"})
            result["failed"] = 1
        elif retries > max_retries:
            page_status = "needs_review"

        # Upsert page
        if existing_page:
            existing_page.content = content
            existing_page.status = page_status
            existing_page.generation_count = (existing_page.generation_count or 0) + 1
            existing_page.updated_at = datetime.now(timezone.utc)
        else:
            new_page = SeoPage(
                city_id=city.id,
                district_id=district.id,
                service_id=service.id,
                slug=page_slug,
                title=f"{service.name} - {district.name}{city.name}",
                h1=f"{city.name}{district.name}{service.name}服务",
                content=content,
                status=page_status,
                generation_count=1,
            )
            session.add(new_page)

        if result["failed"] == 0:
            result["created"] = 1

        job.status = "done"
        job.result = result
        job.error_log = error_log
        job.finished_at = datetime.now(timezone.utc)
        await session.commit()


async def generate_batch_pages(
    ctx: dict,
    job_id: str,
    city_slugs: list[str],
    force: bool = False,
) -> None:
    """ARQ task: batch generate SEO pages for given cities."""
    session_factory = _make_session_factory()

    async with session_factory() as session:
        # Update job status
        job = await session.get(GenerationJob, uuid.UUID(job_id))
        if not job:
            log.error("worker.job_not_found", job_id=job_id)
            return
        job.status = "running"
        await session.commit()

        # Resolve cities
        if city_slugs:
            cities_result = await session.execute(
                select(City).where(City.slug.in_(city_slugs), City.is_active.is_(True))
            )
        else:
            cities_result = await session.execute(
                select(City).where(City.is_active.is_(True))
            )
        cities = cities_result.scalars().all()

        # Fetch active districts and services
        districts_result = await session.execute(
            select(District).where(District.is_active.is_(True))
        )
        all_districts = districts_result.scalars().all()

        services_result = await session.execute(
            select(Service).where(Service.is_active.is_(True))
        )
        services = services_result.scalars().all()

        total = 0
        created = 0
        skipped = 0
        failed = 0
        error_log = []

        for city in cities:
            city_districts = [d for d in all_districts if d.city_id == city.id]
            for district in city_districts:
                for service in services:
                    total += 1
                    page_slug = f"{city.pinyin or city.slug}/{district.slug}/{service.slug}"

                    # Update running counts
                    job.result = {
                        "total": total,
                        "created": created,
                        "skipped": skipped,
                        "failed": failed,
                    }
                    await session.commit()

                    # Check existing
                    existing_row = await session.execute(
                        select(SeoPage).where(SeoPage.slug == page_slug)
                    )
                    existing_page = existing_row.scalar_one_or_none()

                    if existing_page and not force:
                        skipped += 1
                        continue

                    # Generate content
                    content = None
                    retries = 0
                    existing_contents = await _get_existing_service_contents(
                        session, service.id, exclude_slug=page_slug
                    )

                    while retries <= settings.MAX_RETRIES:
                        try:
                            generated = await generate_seo_content(
                                city_name=city.name,
                                district_name=district.name,
                                service_name=service.name,
                                service_description=service.description or "",
                                base_price=service.base_price,
                                landmarks=district.landmarks or [],
                                keywords=service.keywords or [],
                            )
                            if is_duplicate(generated, existing_contents):
                                retries += 1
                                if retries > settings.MAX_RETRIES:
                                    content = generated
                                    break
                                continue
                            content = generated
                            break
                        except Exception as exc:
                            log.error("worker.ai_error", slug=page_slug, error=str(exc))
                            retries += 1
                            if retries > settings.MAX_RETRIES:
                                error_log.append({"slug": page_slug, "error": str(exc)})
                                failed += 1
                                content = None
                                break

                    if content is None and retries > settings.MAX_RETRIES:
                        continue

                    page_status = "draft"
                    if retries > settings.MAX_RETRIES:
                        page_status = "needs_review"

                    if existing_page:
                        existing_page.content = content
                        existing_page.status = page_status
                        existing_page.generation_count = (existing_page.generation_count or 0) + 1
                        existing_page.updated_at = datetime.now(timezone.utc)
                    else:
                        new_page = SeoPage(
                            city_id=city.id,
                            district_id=district.id,
                            service_id=service.id,
                            slug=page_slug,
                            title=f"{service.name} - {district.name}{city.name}",
                            h1=f"{city.name}{district.name}{service.name}服务",
                            content=content,
                            status=page_status,
                            generation_count=1,
                        )
                        session.add(new_page)

                    created += 1
                    await session.commit()

        job.status = "done"
        job.result = {
            "total": total,
            "created": created,
            "skipped": skipped,
            "failed": failed,
        }
        job.error_log = error_log
        job.finished_at = datetime.now(timezone.utc)
        await session.commit()


from arq.connections import RedisSettings


class WorkerSettings:
    functions = [generate_single_page, generate_batch_pages]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)

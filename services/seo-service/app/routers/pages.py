"""SEO page CRUD router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.city import City
from app.models.seo_page import SeoPage
from app.models.service import Service
from app.schemas import SeoPageListResponse, SeoPageOut, SeoPageUpdate

router = APIRouter()


@router.get("", response_model=SeoPageListResponse)
async def list_pages(
    city_slug: str | None = Query(None),
    service_slug: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SeoPage)

    if city_slug:
        city_sub = select(City.id).where(City.slug == city_slug).scalar_subquery()
        stmt = stmt.where(SeoPage.city_id == city_sub)

    if service_slug:
        service_sub = select(Service.id).where(Service.slug == service_slug).scalar_subquery()
        stmt = stmt.where(SeoPage.service_id == service_sub)

    if status:
        stmt = stmt.where(SeoPage.status == status)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return SeoPageListResponse(
        items=[SeoPageOut.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{slug:path}", response_model=SeoPageOut)
async def get_page(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SeoPage).where(SeoPage.slug == slug))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail=f"Page not found: {slug}")
    return SeoPageOut.model_validate(page)


@router.patch("/{slug:path}", response_model=SeoPageOut)
async def update_page(
    slug: str,
    payload: SeoPageUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SeoPage).where(SeoPage.slug == slug))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail=f"Page not found: {slug}")

    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(page, field, value)

    await db.commit()
    await db.refresh(page)
    return SeoPageOut.model_validate(page)

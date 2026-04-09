"""Admin router for city, district and service management."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.city import City
from app.models.district import District
from app.models.service import Service
from app.schemas import (
    CityCreate,
    CityOut,
    CityUpdate,
    DistrictCreate,
    DistrictOut,
    DistrictUpdate,
    ServiceCreate,
    ServiceOut,
    ServiceUpdate,
)

router = APIRouter()


# ─── Cities ──────────────────────────────────────────────────────────────────

@router.get("/cities", response_model=list[CityOut])
async def list_cities(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(City).order_by(City.id))
    return [CityOut.model_validate(c) for c in result.scalars().all()]


@router.post("/cities", response_model=CityOut, status_code=201)
async def create_city(payload: CityCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(City).where(City.slug == payload.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"City slug already exists: {payload.slug}")
    city = City(**payload.model_dump())
    db.add(city)
    await db.commit()
    await db.refresh(city)
    return CityOut.model_validate(city)


@router.patch("/cities/{slug}", response_model=CityOut)
async def update_city(slug: str, payload: CityUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(City).where(City.slug == slug))
    city = result.scalar_one_or_none()
    if not city:
        raise HTTPException(status_code=404, detail=f"City not found: {slug}")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(city, field, value)
    await db.commit()
    await db.refresh(city)
    return CityOut.model_validate(city)


# ─── Districts ───────────────────────────────────────────────────────────────

@router.get("/districts", response_model=list[DistrictOut])
async def list_districts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(District).order_by(District.id))
    return [DistrictOut.model_validate(d) for d in result.scalars().all()]


@router.post("/districts", response_model=DistrictOut, status_code=201)
async def create_district(payload: DistrictCreate, db: AsyncSession = Depends(get_db)):
    # Validate city exists
    city = await db.get(City, payload.city_id)
    if not city:
        raise HTTPException(status_code=404, detail=f"City not found: id={payload.city_id}")
    district = District(**payload.model_dump())
    db.add(district)
    await db.commit()
    await db.refresh(district)
    return DistrictOut.model_validate(district)


@router.patch("/districts/{district_id}", response_model=DistrictOut)
async def update_district(
    district_id: int, payload: DistrictUpdate, db: AsyncSession = Depends(get_db)
):
    district = await db.get(District, district_id)
    if not district:
        raise HTTPException(status_code=404, detail=f"District not found: id={district_id}")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(district, field, value)
    await db.commit()
    await db.refresh(district)
    return DistrictOut.model_validate(district)


# ─── Services ────────────────────────────────────────────────────────────────

@router.get("/services", response_model=list[ServiceOut])
async def list_services(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Service).order_by(Service.id))
    return [ServiceOut.model_validate(s) for s in result.scalars().all()]


@router.post("/services", response_model=ServiceOut, status_code=201)
async def create_service(payload: ServiceCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Service).where(Service.slug == payload.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail=f"Service slug already exists: {payload.slug}"
        )
    service = Service(**payload.model_dump())
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return ServiceOut.model_validate(service)


@router.patch("/services/{slug}", response_model=ServiceOut)
async def update_service(slug: str, payload: ServiceUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Service).where(Service.slug == slug))
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail=f"Service not found: {slug}")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(service, field, value)
    await db.commit()
    await db.refresh(service)
    return ServiceOut.model_validate(service)

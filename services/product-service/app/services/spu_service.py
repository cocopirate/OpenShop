"""Business logic for SPU management."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.spu import Spu, SpuStatus
from app.schemas.spu import SpuCreate, SpuUpdate


async def get_spu(db: AsyncSession, spu_id: int) -> Spu | None:
    result = await db.execute(select(Spu).where(Spu.id == spu_id))
    return result.scalar_one_or_none()


async def list_spus(
    db: AsyncSession,
    category_id: Optional[int] = None,
    status: Optional[SpuStatus] = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[Spu], int]:
    query = select(Spu)
    count_query = select(func.count()).select_from(Spu)

    if category_id is not None:
        query = query.where(Spu.category_id == category_id)
        count_query = count_query.where(Spu.category_id == category_id)
    if status is not None:
        query = query.where(Spu.status == status)
        count_query = count_query.where(Spu.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Spu.id.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total


async def create_spu(db: AsyncSession, data: SpuCreate) -> Spu:
    spu = Spu(**data.model_dump())
    db.add(spu)
    await db.flush()
    await db.refresh(spu)
    return spu


async def update_spu(db: AsyncSession, spu_id: int, data: SpuUpdate) -> Spu | None:
    spu = await get_spu(db, spu_id)
    if not spu:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(spu, k, v)
    await db.flush()
    await db.refresh(spu)
    return spu


async def publish_spu(db: AsyncSession, spu_id: int) -> Spu | None:
    spu = await get_spu(db, spu_id)
    if not spu:
        return None
    spu.status = SpuStatus.ONLINE
    await db.flush()
    await db.refresh(spu)
    return spu


async def unpublish_spu(db: AsyncSession, spu_id: int) -> Spu | None:
    spu = await get_spu(db, spu_id)
    if not spu:
        return None
    spu.status = SpuStatus.OFFLINE
    await db.flush()
    await db.refresh(spu)
    return spu


async def list_online_spus(
    db: AsyncSession,
    category_id: Optional[int] = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[Spu], int]:
    return await list_spus(db, category_id=category_id, status=SpuStatus.ONLINE, page=page, size=size)

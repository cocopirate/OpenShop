"""Business logic for SKU management."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sku import Sku
from app.schemas.sku import SkuCreate, SkuUpdate


async def get_sku(db: AsyncSession, sku_id: int) -> Sku | None:
    result = await db.execute(select(Sku).where(Sku.id == sku_id))
    return result.scalar_one_or_none()


async def list_skus_by_spu(db: AsyncSession, spu_id: int) -> list[Sku]:
    result = await db.execute(select(Sku).where(Sku.spu_id == spu_id).order_by(Sku.id))
    return list(result.scalars().all())


async def batch_create_skus(db: AsyncSession, items: list[SkuCreate]) -> list[Sku]:
    skus = [Sku(**item.model_dump()) for item in items]
    db.add_all(skus)
    await db.flush()
    for sku in skus:
        await db.refresh(sku)
    return skus


async def update_sku(db: AsyncSession, sku_id: int, data: SkuUpdate) -> Sku | None:
    sku = await get_sku(db, sku_id)
    if not sku:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(sku, k, v)
    await db.flush()
    await db.refresh(sku)
    return sku


async def delete_sku(db: AsyncSession, sku_id: int) -> bool:
    sku = await get_sku(db, sku_id)
    if not sku:
        return False
    await db.delete(sku)
    await db.flush()
    return True

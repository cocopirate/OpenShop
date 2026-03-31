"""Business logic for ProductGroup management."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product_group import ProductGroup, ProductGroupItem
from app.models.spu import Spu, SpuStatus
from app.schemas.product_group import GroupItemCreate, ProductGroupCreate, ProductGroupUpdate


async def get_group(db: AsyncSession, group_id: int) -> ProductGroup | None:
    result = await db.execute(select(ProductGroup).where(ProductGroup.id == group_id))
    return result.scalar_one_or_none()


async def list_groups(db: AsyncSession) -> list[ProductGroup]:
    result = await db.execute(select(ProductGroup).order_by(ProductGroup.id))
    return list(result.scalars().all())


async def create_group(db: AsyncSession, data: ProductGroupCreate) -> ProductGroup:
    group = ProductGroup(**data.model_dump())
    db.add(group)
    await db.flush()
    await db.refresh(group)
    return group


async def update_group(db: AsyncSession, group_id: int, data: ProductGroupUpdate) -> ProductGroup | None:
    group = await get_group(db, group_id)
    if not group:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(group, k, v)
    await db.flush()
    await db.refresh(group)
    return group


async def delete_group(db: AsyncSession, group_id: int) -> bool:
    group = await get_group(db, group_id)
    if not group:
        return False
    # Remove all items first
    items = await list_group_items(db, group_id)
    for item in items:
        await db.delete(item)
    await db.delete(group)
    await db.flush()
    return True


async def list_group_items(db: AsyncSession, group_id: int) -> list[ProductGroupItem]:
    result = await db.execute(
        select(ProductGroupItem)
        .where(ProductGroupItem.group_id == group_id)
        .order_by(ProductGroupItem.sort_order, ProductGroupItem.spu_id)
    )
    return list(result.scalars().all())


async def list_group_spus(db: AsyncSession, group_id: int) -> list[Spu]:
    result = await db.execute(
        select(Spu)
        .join(ProductGroupItem, Spu.id == ProductGroupItem.spu_id)
        .where(
            ProductGroupItem.group_id == group_id,
            Spu.status == SpuStatus.ONLINE,
        )
        .order_by(ProductGroupItem.sort_order, ProductGroupItem.spu_id)
    )
    return list(result.scalars().all())


async def add_group_product(
    db: AsyncSession, group_id: int, data: GroupItemCreate
) -> tuple[ProductGroupItem | None, str | None]:
    # Check if already added
    existing = await db.execute(
        select(ProductGroupItem).where(
            ProductGroupItem.group_id == group_id,
            ProductGroupItem.spu_id == data.spu_id,
        )
    )
    if existing.scalar_one_or_none():
        return None, "duplicate"

    item = ProductGroupItem(group_id=group_id, spu_id=data.spu_id, sort_order=data.sort_order)
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item, None


async def remove_group_product(db: AsyncSession, group_id: int, spu_id: int) -> bool:
    result = await db.execute(
        select(ProductGroupItem).where(
            ProductGroupItem.group_id == group_id,
            ProductGroupItem.spu_id == spu_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        return False
    await db.delete(item)
    await db.flush()
    return True

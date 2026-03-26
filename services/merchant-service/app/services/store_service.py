from __future__ import annotations
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.store import MerchantStore
from app.schemas.store import StoreCreate, StoreUpdate


async def list_stores(db: AsyncSession, merchant_id: int, page: int = 1, page_size: int = 20):
    q = select(MerchantStore).where(MerchantStore.merchant_id == merchant_id)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    items = (await db.execute(q.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return list(items), total


async def get_store(db: AsyncSession, store_id: int) -> MerchantStore | None:
    result = await db.execute(select(MerchantStore).where(MerchantStore.id == store_id))
    return result.scalar_one_or_none()


async def create_store(db: AsyncSession, merchant_id: int, data: StoreCreate) -> MerchantStore:
    store = MerchantStore(merchant_id=merchant_id, **data.model_dump(exclude_none=True))
    db.add(store)
    await db.flush()
    await db.refresh(store)
    return store


async def update_store(db: AsyncSession, store_id: int, data: StoreUpdate) -> MerchantStore | None:
    store = await get_store(db, store_id)
    if not store:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(store, k, v)
    await db.flush()
    return store


async def delete_store(db: AsyncSession, store_id: int) -> None:
    store = await get_store(db, store_id)
    if store:
        await db.delete(store)
        await db.flush()

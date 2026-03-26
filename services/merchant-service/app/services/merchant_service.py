from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.merchant import MerchantAccount
from app.schemas.merchant import MerchantCreate, MerchantUpdate
import uuid6


async def get_merchant(db: AsyncSession, merchant_id: int) -> MerchantAccount | None:
    result = await db.execute(select(MerchantAccount).where(MerchantAccount.id == merchant_id))
    return result.scalar_one_or_none()


async def create_merchant(db: AsyncSession, data: MerchantCreate) -> MerchantAccount:
    merchant = MerchantAccount(
        public_id=uuid6.uuid7(),
        **data.model_dump(exclude_none=True),
        status=0,
    )
    db.add(merchant)
    await db.flush()
    await db.refresh(merchant)
    return merchant


async def update_merchant(db: AsyncSession, merchant_id: int, data: MerchantUpdate) -> MerchantAccount | None:
    merchant = await get_merchant(db, merchant_id)
    if not merchant:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(merchant, k, v)
    await db.flush()
    return merchant


async def update_merchant_status(db: AsyncSession, merchant_id: int, status: int) -> MerchantAccount | None:
    merchant = await get_merchant(db, merchant_id)
    if not merchant:
        return None
    merchant.status = status
    if status == 1:
        merchant.verified_at = datetime.now(timezone.utc)
    await db.flush()
    return merchant

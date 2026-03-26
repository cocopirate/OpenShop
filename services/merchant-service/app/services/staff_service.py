from __future__ import annotations
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.staff import MerchantStaff
from app.models.rbac import merchant_account_role
from app.schemas.staff import StaffCreate, StaffUpdate


async def list_staff(db: AsyncSession, merchant_id: int, page: int = 1, page_size: int = 20):
    q = select(MerchantStaff).where(MerchantStaff.merchant_id == merchant_id)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    items = (await db.execute(q.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return list(items), total


async def get_staff(db: AsyncSession, staff_id: int) -> MerchantStaff | None:
    result = await db.execute(select(MerchantStaff).where(MerchantStaff.id == staff_id))
    return result.scalar_one_or_none()


async def create_staff(db: AsyncSession, merchant_id: int, data: StaffCreate) -> MerchantStaff:
    staff = MerchantStaff(merchant_id=merchant_id, **data.model_dump(exclude_none=True))
    db.add(staff)
    await db.flush()
    await db.refresh(staff)
    return staff


async def update_staff(db: AsyncSession, staff_id: int, data: StaffUpdate) -> MerchantStaff | None:
    staff = await get_staff(db, staff_id)
    if not staff:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(staff, k, v)
    await db.flush()
    return staff


async def delete_staff(db: AsyncSession, staff_id: int) -> None:
    staff = await get_staff(db, staff_id)
    if staff:
        await db.delete(staff)
        await db.flush()


async def assign_roles(db: AsyncSession, staff_id: int, role_ids: list[int]) -> None:
    await db.execute(
        delete(merchant_account_role).where(
            merchant_account_role.c.account_id == staff_id,
            merchant_account_role.c.account_type == 2,
        )
    )
    for rid in role_ids:
        await db.execute(
            merchant_account_role.insert().values(account_id=staff_id, account_type=2, role_id=rid)
        )
    await db.flush()

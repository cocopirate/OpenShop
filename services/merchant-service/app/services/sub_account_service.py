from __future__ import annotations
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.sub_account import MerchantSubAccount
from app.models.rbac import MerchantRole, MerchantPermission, merchant_account_role
from app.schemas.sub_account import SubAccountCreate, SubAccountUpdate


async def list_sub_accounts(db: AsyncSession, merchant_id: int, page: int = 1, page_size: int = 20):
    q = select(MerchantSubAccount).where(MerchantSubAccount.merchant_id == merchant_id)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    items = (await db.execute(q.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return list(items), total


async def get_sub_account(db: AsyncSession, sub_id: int) -> MerchantSubAccount | None:
    result = await db.execute(select(MerchantSubAccount).where(MerchantSubAccount.id == sub_id))
    return result.scalar_one_or_none()


async def create_sub_account(db: AsyncSession, merchant_id: int, data: SubAccountCreate) -> MerchantSubAccount:
    sub = MerchantSubAccount(merchant_id=merchant_id, **data.model_dump(exclude_none=True))
    db.add(sub)
    await db.flush()
    await db.refresh(sub)
    return sub


async def update_sub_account(db: AsyncSession, sub_id: int, data: SubAccountUpdate) -> MerchantSubAccount | None:
    sub = await get_sub_account(db, sub_id)
    if not sub:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(sub, k, v)
    await db.flush()
    return sub


async def delete_sub_account(db: AsyncSession, sub_id: int) -> None:
    sub = await get_sub_account(db, sub_id)
    if sub:
        await db.delete(sub)
        await db.flush()


async def assign_roles(db: AsyncSession, sub_id: int, role_ids: list[int]) -> None:
    await db.execute(
        delete(merchant_account_role).where(
            merchant_account_role.c.account_id == sub_id,
            merchant_account_role.c.account_type == 1,
        )
    )
    for rid in role_ids:
        await db.execute(
            merchant_account_role.insert().values(account_id=sub_id, account_type=1, role_id=rid)
        )
    await db.flush()


async def get_permissions(db: AsyncSession, sub_id: int) -> list[str]:
    # Load roles for this sub-account
    role_ids_result = await db.execute(
        select(merchant_account_role.c.role_id).where(
            merchant_account_role.c.account_id == sub_id,
            merchant_account_role.c.account_type == 1,
        )
    )
    role_ids = [r for (r,) in role_ids_result.all()]
    if not role_ids:
        return []
    roles_result = await db.execute(
        select(MerchantRole).where(MerchantRole.id.in_(role_ids)).options(
            selectinload(MerchantRole.permissions)
        )
    )
    perms: set[str] = set()
    for role in roles_result.scalars().all():
        for p in role.permissions:
            perms.add(p.perm_code)
    return list(perms)

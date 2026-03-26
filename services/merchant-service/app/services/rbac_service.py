from __future__ import annotations
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.rbac import MerchantRole, MerchantPermission, merchant_role_permission
from app.schemas.rbac import RoleCreate, RoleUpdate


async def list_roles(db: AsyncSession, merchant_id: int) -> list[MerchantRole]:
    result = await db.execute(select(MerchantRole).where(MerchantRole.merchant_id == merchant_id))
    return list(result.scalars().all())


async def get_role(db: AsyncSession, role_id: int) -> MerchantRole | None:
    result = await db.execute(select(MerchantRole).where(MerchantRole.id == role_id))
    return result.scalar_one_or_none()


async def create_role(db: AsyncSession, merchant_id: int, data: RoleCreate) -> MerchantRole:
    role = MerchantRole(merchant_id=merchant_id, **data.model_dump())
    db.add(role)
    await db.flush()
    await db.refresh(role)
    return role


async def delete_role(db: AsyncSession, role_id: int) -> bool:
    role = await get_role(db, role_id)
    if not role:
        return False
    if role.is_system:
        return False
    await db.delete(role)
    await db.flush()
    return True


async def assign_permissions(db: AsyncSession, role_id: int, permission_ids: list[int]) -> None:
    await db.execute(
        delete(merchant_role_permission).where(merchant_role_permission.c.role_id == role_id)
    )
    for pid in permission_ids:
        await db.execute(
            merchant_role_permission.insert().values(role_id=role_id, permission_id=pid)
        )
    await db.flush()


async def list_permissions(db: AsyncSession) -> list[MerchantPermission]:
    result = await db.execute(select(MerchantPermission))
    return list(result.scalars().all())

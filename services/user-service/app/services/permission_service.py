from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import Permission, PermissionType
from app.schemas.permission import PermissionCreate, PermissionUpdate


async def get_permissions(db: AsyncSession) -> list[Permission]:
    result = await db.execute(select(Permission))
    return list(result.scalars().all())


async def get_permission(db: AsyncSession, perm_id: int) -> Optional[Permission]:
    result = await db.execute(select(Permission).where(Permission.id == perm_id))
    return result.scalar_one_or_none()


async def create_permission(db: AsyncSession, data: PermissionCreate) -> Permission:
    perm = Permission(
        code=data.code,
        name=data.name,
        type=PermissionType(data.type),
        method=data.method,
        path=data.path,
        parent_id=data.parent_id,
    )
    db.add(perm)
    await db.flush()
    await db.refresh(perm)
    return perm


async def update_permission(
    db: AsyncSession, perm_id: int, data: PermissionUpdate
) -> Optional[Permission]:
    perm = await get_permission(db, perm_id)
    if perm is None:
        return None
    if data.code is not None:
        perm.code = data.code
    if data.name is not None:
        perm.name = data.name
    if data.type is not None:
        perm.type = PermissionType(data.type)
    if data.method is not None:
        perm.method = data.method
    if data.path is not None:
        perm.path = data.path
    if data.parent_id is not None:
        perm.parent_id = data.parent_id
    await db.flush()
    await db.refresh(perm)
    return perm


async def delete_permission(db: AsyncSession, perm_id: int) -> bool:
    perm = await get_permission(db, perm_id)
    if perm is None:
        return False
    await db.delete(perm)
    await db.flush()
    return True

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import AdminPermission
from app.schemas.permission import AdminPermissionCreate, AdminPermissionResponse, AdminPermissionUpdate


async def get_permissions(db: AsyncSession) -> list[AdminPermission]:
    result = await db.execute(select(AdminPermission))
    return list(result.scalars().all())


async def get_permission(db: AsyncSession, perm_id: int) -> Optional[AdminPermission]:
    result = await db.execute(select(AdminPermission).where(AdminPermission.id == perm_id))
    return result.scalar_one_or_none()


async def create_permission(db: AsyncSession, data: AdminPermissionCreate) -> AdminPermission:
    perm = AdminPermission(
        parent_id=data.parent_id,
        perm_code=data.perm_code,
        perm_name=data.perm_name,
        perm_type=data.perm_type,
        path=data.path,
        method=data.method,
    )
    db.add(perm)
    await db.flush()
    await db.refresh(perm)
    return perm


async def update_permission(
    db: AsyncSession, perm_id: int, data: AdminPermissionUpdate
) -> Optional[AdminPermission]:
    perm = await get_permission(db, perm_id)
    if perm is None:
        return None
    if data.parent_id is not None:
        perm.parent_id = data.parent_id
    if data.perm_code is not None:
        perm.perm_code = data.perm_code
    if data.perm_name is not None:
        perm.perm_name = data.perm_name
    if data.perm_type is not None:
        perm.perm_type = data.perm_type
    if data.path is not None:
        perm.path = data.path
    if data.method is not None:
        perm.method = data.method
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


def build_permission_tree(
    perms: list[AdminPermission],
) -> list[AdminPermissionResponse]:
    """Build a nested permission tree from a flat list."""
    perm_map: dict[int, AdminPermissionResponse] = {}
    for p in perms:
        perm_map[p.id] = AdminPermissionResponse.model_validate(p)

    roots: list[AdminPermissionResponse] = []
    for p in perms:
        node = perm_map[p.id]
        if p.parent_id == 0 or p.parent_id not in perm_map:
            roots.append(node)
        else:
            perm_map[p.parent_id].children.append(node)
    return roots

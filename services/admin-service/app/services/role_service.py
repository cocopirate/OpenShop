from __future__ import annotations

import json
from typing import Optional

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.admin import AdminAccount
from app.models.permission import AdminPermission
from app.models.role import AdminRole
from app.schemas.role import AdminRoleCreate, AdminRoleUpdate

_PERM_CACHE_TTL = 86400


async def get_roles(db: AsyncSession) -> list[AdminRole]:
    result = await db.execute(select(AdminRole))
    return list(result.scalars().all())


async def get_role(db: AsyncSession, role_id: int) -> Optional[AdminRole]:
    result = await db.execute(select(AdminRole).where(AdminRole.id == role_id))
    return result.scalar_one_or_none()


async def create_role(db: AsyncSession, data: AdminRoleCreate) -> AdminRole:
    role = AdminRole(
        role_code=data.role_code,
        role_name=data.role_name,
        is_system=data.is_system,
        status=data.status,
    )
    db.add(role)
    await db.flush()
    await db.refresh(role)
    return role


async def update_role(
    db: AsyncSession, role_id: int, data: AdminRoleUpdate
) -> Optional[AdminRole]:
    role = await get_role(db, role_id)
    if role is None:
        return None
    if data.role_code is not None:
        role.role_code = data.role_code
    if data.role_name is not None:
        role.role_name = data.role_name
    if data.status is not None:
        role.status = data.status
    await db.flush()
    await db.refresh(role)
    return role


async def delete_role(db: AsyncSession, role_id: int) -> tuple[bool, str]:
    """Returns (success, error_message). System roles cannot be deleted."""
    role = await get_role(db, role_id)
    if role is None:
        return False, "not_found"
    if role.is_system == 1:
        return False, "system_role"
    await db.delete(role)
    await db.flush()
    return True, ""


async def assign_permissions_to_role(
    db: AsyncSession, redis: Redis, role_id: int, permission_ids: list[int]
) -> Optional[AdminRole]:
    result = await db.execute(
        select(AdminRole).where(AdminRole.id == role_id).options(selectinload(AdminRole.permissions))
    )
    role = result.scalar_one_or_none()
    if role is None:
        return None

    perms_result = await db.execute(
        select(AdminPermission).where(AdminPermission.id.in_(permission_ids))
    )
    perms = list(perms_result.scalars().all())
    role.permissions = perms
    await db.flush()
    await db.refresh(role)

    # Invalidate Redis cache only for admins that have this role
    from app.models.admin import admin_account_role as _aar  # local import to avoid circular

    admins_result = await db.execute(
        select(AdminAccount)
        .join(_aar, _aar.c.admin_id == AdminAccount.id)
        .where(_aar.c.role_id == role_id)
        .options(selectinload(AdminAccount.roles).selectinload(AdminRole.permissions))
    )
    admins = list(admins_result.scalars().all())
    for admin in admins:
        perm_codes: set[str] = set()
        for r in admin.roles:
            for p in r.permissions:
                perm_codes.add(p.perm_code)
        await redis.set(
            f"admin_permissions:{admin.id}", json.dumps(list(perm_codes)), ex=_PERM_CACHE_TTL
        )

    return role

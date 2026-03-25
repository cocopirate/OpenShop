from __future__ import annotations

import json
from typing import Optional

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.permission import Permission
from app.models.role import Role
from app.models.user import AdminUser
from app.schemas.role import RoleCreate, RoleUpdate


async def get_roles(db: AsyncSession) -> list[Role]:
    result = await db.execute(select(Role))
    return list(result.scalars().all())


async def get_role(db: AsyncSession, role_id: int) -> Optional[Role]:
    result = await db.execute(select(Role).where(Role.id == role_id))
    return result.scalar_one_or_none()


async def create_role(db: AsyncSession, data: RoleCreate) -> Role:
    role = Role(name=data.name, desc=data.desc)
    db.add(role)
    await db.flush()
    await db.refresh(role)
    return role


async def update_role(db: AsyncSession, role_id: int, data: RoleUpdate) -> Optional[Role]:
    role = await get_role(db, role_id)
    if role is None:
        return None
    if data.name is not None:
        role.name = data.name
    if data.desc is not None:
        role.desc = data.desc
    await db.flush()
    await db.refresh(role)
    return role


async def delete_role(db: AsyncSession, role_id: int) -> bool:
    role = await get_role(db, role_id)
    if role is None:
        return False
    await db.delete(role)
    await db.flush()
    return True


async def assign_permissions_to_role(
    db: AsyncSession, redis: Redis, role_id: int, permission_ids: list[int]
) -> Optional[Role]:
    result = await db.execute(
        select(Role).where(Role.id == role_id).options(selectinload(Role.permissions))
    )
    role = result.scalar_one_or_none()
    if role is None:
        return None

    perms_result = await db.execute(
        select(Permission).where(Permission.id.in_(permission_ids))
    )
    perms = list(perms_result.scalars().all())
    role.permissions = perms
    await db.flush()
    await db.refresh(role)

    # Update Redis for all admin users who have this role
    admin_users_result = await db.execute(
        select(AdminUser).options(selectinload(AdminUser.roles).selectinload(Role.permissions))
    )
    admin_users = list(admin_users_result.scalars().all())
    for user in admin_users:
        has_role = any(r.id == role_id for r in user.roles)
        if not has_role:
            continue
        perm_codes: set[str] = set()
        for r in user.roles:
            if r.id == role_id:
                perm_codes.update(p.code for p in perms)
            else:
                perm_codes.update(p.code for p in r.permissions)
        ver_key = f"user_perm_ver:{user.id}"
        await redis.incr(ver_key)
        await redis.expire(ver_key, 86400)
        await redis.set(f"user_permissions:{user.id}", json.dumps(list(perm_codes)), ex=86400)

    return role

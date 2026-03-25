from __future__ import annotations

import json
from typing import Optional
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.models.role import Role
from app.models.user import AdminUser, AdminUserStatus
from app.schemas.user import AdminUserCreate, AdminUserUpdate


async def get_users(db: AsyncSession) -> list[AdminUser]:
    result = await db.execute(select(AdminUser))
    return list(result.scalars().all())


async def get_user(db: AsyncSession, user_id: int) -> Optional[AdminUser]:
    """Internal lookup by integer PK. Use get_user_by_public_id for external API."""
    result = await db.execute(select(AdminUser).where(AdminUser.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_public_id(db: AsyncSession, public_id: UUID) -> Optional[AdminUser]:
    result = await db.execute(select(AdminUser).where(AdminUser.public_id == public_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, data: AdminUserCreate) -> AdminUser:
    user = AdminUser(
        username=data.username,
        hashed_password=hash_password(data.password),
        status=AdminUserStatus(data.status),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, public_id: UUID, data: AdminUserUpdate) -> Optional[AdminUser]:
    user = await get_user_by_public_id(db, public_id)
    if user is None:
        return None
    if data.username is not None:
        user.username = data.username
    if data.status is not None:
        user.status = AdminUserStatus(data.status)
    await db.flush()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, public_id: UUID) -> bool:
    user = await get_user_by_public_id(db, public_id)
    if user is None:
        return False
    await db.delete(user)
    await db.flush()
    return True


async def update_user_status(
    db: AsyncSession, redis: Redis, public_id: UUID, status: str
) -> Optional[AdminUser]:
    user = await get_user_by_public_id(db, public_id)
    if user is None:
        return None
    user.status = AdminUserStatus(status)
    await db.flush()
    await db.refresh(user)
    await redis.set(f"user_status:{user.id}", status, ex=86400)
    return user


async def assign_roles_to_user(
    db: AsyncSession, redis: Redis, public_id: UUID, role_ids: list[int]
) -> Optional[AdminUser]:
    result = await db.execute(
        select(AdminUser)
        .where(AdminUser.public_id == public_id)
        .options(selectinload(AdminUser.roles).selectinload(Role.permissions))
    )
    user = result.scalar_one_or_none()
    if user is None:
        return None

    roles_result = await db.execute(select(Role).where(Role.id.in_(role_ids)))
    roles = list(roles_result.scalars().all())
    user.roles = roles
    await db.flush()
    await db.refresh(user)

    # Recompute permissions
    perm_codes: set[str] = set()
    for role in user.roles:
        for perm in role.permissions:
            perm_codes.add(perm.code)

    # Increment perm version
    ver_key = f"user_perm_ver:{user.public_id}"
    await redis.incr(ver_key)
    await redis.expire(ver_key, 86400)
    await redis.set(f"user_permissions:{user.public_id}", json.dumps(list(perm_codes)), ex=86400)
    return user


async def get_user_permissions(db: AsyncSession, user_id: int) -> list[str]:
    result = await db.execute(
        select(AdminUser)
        .where(AdminUser.id == user_id)
        .options(selectinload(AdminUser.roles).selectinload(Role.permissions))
    )
    user = result.scalar_one_or_none()
    if user is None:
        return []
    codes: set[str] = set()
    for role in user.roles:
        for perm in role.permissions:
            codes.add(perm.code)
    return list(codes)

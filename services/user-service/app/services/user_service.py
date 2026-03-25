from __future__ import annotations

import json
from typing import Optional

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User, UserStatus
from app.schemas.user import UserCreate, UserUpdate


async def get_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User))
    return list(result.scalars().all())


async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    user = User(
        username=data.username,
        hashed_password=hash_password(data.password),
        status=UserStatus(data.status),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, user_id: int, data: UserUpdate) -> Optional[User]:
    user = await get_user(db, user_id)
    if user is None:
        return None
    if data.username is not None:
        user.username = data.username
    if data.status is not None:
        user.status = UserStatus(data.status)
    await db.flush()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user_id: int) -> bool:
    user = await get_user(db, user_id)
    if user is None:
        return False
    await db.delete(user)
    await db.flush()
    return True


async def update_user_status(
    db: AsyncSession, redis: Redis, user_id: int, status: str
) -> Optional[User]:
    user = await get_user(db, user_id)
    if user is None:
        return None
    user.status = UserStatus(status)
    await db.flush()
    await db.refresh(user)
    await redis.set(f"user_status:{user_id}", status, ex=86400)
    return user


async def assign_roles_to_user(
    db: AsyncSession, redis: Redis, user_id: int, role_ids: list[int]
) -> Optional[User]:
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.roles).selectinload(Role.permissions))
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
    ver_key = f"user_perm_ver:{user_id}"
    await redis.incr(ver_key)
    await redis.expire(ver_key, 86400)
    await redis.set(f"user_permissions:{user_id}", json.dumps(list(perm_codes)), ex=86400)
    return user


async def get_user_permissions(db: AsyncSession, user_id: int) -> list[str]:
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )
    user = result.scalar_one_or_none()
    if user is None:
        return []
    codes: set[str] = set()
    for role in user.roles:
        for perm in role.permissions:
            codes.add(perm.code)
    return list(codes)

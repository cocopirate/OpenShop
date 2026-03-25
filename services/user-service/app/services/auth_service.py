from __future__ import annotations

import json
from typing import Optional

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.models.role import Role
from app.models.user import AdminUser


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[AdminUser]:
    result = await db.execute(select(AdminUser).where(AdminUser.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def create_token_for_user(db: AsyncSession, redis: Redis, user: AdminUser) -> str:
    """Build JWT payload, cache user data in Redis, return token."""
    result = await db.execute(
        select(AdminUser)
        .where(AdminUser.id == user.id)
        .options(selectinload(AdminUser.roles).selectinload(Role.permissions))
    )
    loaded = result.scalar_one_or_none()

    roles: list[str] = []
    permissions: set[str] = set()
    if loaded:
        for role in loaded.roles:
            roles.append(role.name)
            for perm in role.permissions:
                permissions.add(perm.code)

    perm_list = list(permissions)

    # Get or init perm version
    ver_key = f"user_perm_ver:{user.id}"
    ver = await redis.get(ver_key)
    if ver is None:
        ver = 0
        await redis.set(ver_key, ver, ex=86400)
    else:
        ver = int(ver)

    ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60 + 300

    # Cache in Redis
    status_val = user.status.value if hasattr(user.status, "value") else user.status
    await redis.set(f"user_status:{user.id}", status_val, ex=ttl)
    await redis.set(f"user_permissions:{user.id}", json.dumps(perm_list), ex=86400)

    payload = {
        "uid": str(user.public_id),
        "username": user.username,
        "roles": roles,
        "permissions": perm_list,
        "status": status_val,
        "ver": ver,
    }
    return create_access_token(data=payload)

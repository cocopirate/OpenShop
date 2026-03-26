from __future__ import annotations

import json
import math
from typing import Optional
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.models.admin import AdminAccount
from app.models.permission import AdminPermission
from app.models.role import AdminRole
from app.schemas.admin import AdminAccountCreate, AdminAccountUpdate

_PERM_CACHE_TTL = 86400


async def get_admins(
    db: AsyncSession, page: int = 1, page_size: int = 20
) -> tuple[list[AdminAccount], int]:
    offset = (page - 1) * page_size
    total_result = await db.execute(select(func.count()).select_from(AdminAccount))
    total = total_result.scalar_one()
    result = await db.execute(select(AdminAccount).offset(offset).limit(page_size))
    return list(result.scalars().all()), total


async def get_admin(db: AsyncSession, admin_id: int) -> Optional[AdminAccount]:
    result = await db.execute(select(AdminAccount).where(AdminAccount.id == admin_id))
    return result.scalar_one_or_none()


async def get_admin_by_username(db: AsyncSession, username: str) -> Optional[AdminAccount]:
    result = await db.execute(select(AdminAccount).where(AdminAccount.username == username))
    return result.scalar_one_or_none()


async def create_admin(db: AsyncSession, data: AdminAccountCreate) -> AdminAccount:
    admin = AdminAccount(
        username=data.username,
        password_hash=hash_password(data.password),
        real_name=data.real_name,
        phone=data.phone,
        status=data.status,
        created_by=data.created_by,
    )
    db.add(admin)
    await db.flush()
    await db.refresh(admin)
    return admin


async def update_admin(
    db: AsyncSession, admin_id: int, data: AdminAccountUpdate
) -> Optional[AdminAccount]:
    admin = await get_admin(db, admin_id)
    if admin is None:
        return None
    if data.username is not None:
        admin.username = data.username
    if data.real_name is not None:
        admin.real_name = data.real_name
    if data.phone is not None:
        admin.phone = data.phone
    if data.status is not None:
        admin.status = data.status
    await db.flush()
    await db.refresh(admin)
    return admin


async def delete_admin(db: AsyncSession, admin_id: int) -> bool:
    admin = await get_admin(db, admin_id)
    if admin is None:
        return False
    await db.delete(admin)
    await db.flush()
    return True


async def update_admin_status(
    db: AsyncSession, redis: Redis, admin_id: int, status: int
) -> Optional[AdminAccount]:
    admin = await get_admin(db, admin_id)
    if admin is None:
        return None
    admin.status = status
    await db.flush()
    await db.refresh(admin)
    await redis.set(f"admin_status:{admin_id}", str(status), ex=_PERM_CACHE_TTL)
    return admin


async def assign_roles_to_admin(
    db: AsyncSession, redis: Redis, admin_id: int, role_ids: list[int]
) -> Optional[AdminAccount]:
    result = await db.execute(
        select(AdminAccount)
        .where(AdminAccount.id == admin_id)
        .options(selectinload(AdminAccount.roles).selectinload(AdminRole.permissions))
    )
    admin = result.scalar_one_or_none()
    if admin is None:
        return None

    roles_result = await db.execute(select(AdminRole).where(AdminRole.id.in_(role_ids)))
    roles = list(roles_result.scalars().all())
    admin.roles = roles
    await db.flush()
    await db.refresh(admin)

    perm_codes: set[str] = set()
    for role in admin.roles:
        for perm in role.permissions:
            perm_codes.add(perm.perm_code)

    await redis.set(
        f"admin_permissions:{admin_id}", json.dumps(list(perm_codes)), ex=_PERM_CACHE_TTL
    )
    return admin


async def get_admin_permissions(db: AsyncSession, admin_id: int) -> list[str]:
    result = await db.execute(
        select(AdminAccount)
        .where(AdminAccount.id == admin_id)
        .options(selectinload(AdminAccount.roles).selectinload(AdminRole.permissions))
    )
    admin = result.scalar_one_or_none()
    if admin is None:
        return []
    codes: set[str] = set()
    for role in admin.roles:
        for perm in role.permissions:
            codes.add(perm.perm_code)
    return list(codes)

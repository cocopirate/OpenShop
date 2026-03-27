from __future__ import annotations

import asyncio
import os

from sqlalchemy import select

import app.models  # noqa: F401
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.admin import AdminAccount, admin_account_role
from app.models.permission import AdminPermission
from app.models.role import AdminRole, admin_role_permission


# parent_code 为 None 表示根权限（parent_id=0）
DEFAULT_PERMISSIONS = [
    {
        "perm_code": "admin.dashboard.view",
        "perm_name": "查看仪表盘",
        "perm_type": 1,
        "path": "/dashboard",
        "method": "GET",
        "parent_code": None,
    },
    {
        "perm_code": "admin.admins.view",
        "perm_name": "查看管理员",
        "perm_type": 1,
        "path": "/admins",
        "method": "GET",
        "parent_code": None,
    },
    {
        "perm_code": "admin.admins.create",
        "perm_name": "创建管理员",
        "perm_type": 2,
        "path": "/admins",
        "method": "POST",
        "parent_code": "admin.admins.view",
    },
    {
        "perm_code": "admin.admins.update",
        "perm_name": "更新管理员",
        "perm_type": 2,
        "path": "/admins/{id}",
        "method": "PUT",
        "parent_code": "admin.admins.view",
    },
    {
        "perm_code": "admin.admins.delete",
        "perm_name": "删除管理员",
        "perm_type": 2,
        "path": "/admins/{id}",
        "method": "DELETE",
        "parent_code": "admin.admins.view",
    },
    {
        "perm_code": "admin.admins.assign_roles",
        "perm_name": "分配管理员角色",
        "perm_type": 2,
        "path": "/admins/{id}/roles",
        "method": "POST",
        "parent_code": "admin.admins.view",
    },
    {
        "perm_code": "admin.roles.view",
        "perm_name": "查看角色",
        "perm_type": 1,
        "path": "/roles",
        "method": "GET",
        "parent_code": None,
    },
    {
        "perm_code": "admin.roles.create",
        "perm_name": "创建角色",
        "perm_type": 2,
        "path": "/roles",
        "method": "POST",
        "parent_code": "admin.roles.view",
    },
    {
        "perm_code": "admin.roles.update",
        "perm_name": "更新角色",
        "perm_type": 2,
        "path": "/roles/{id}",
        "method": "PUT",
        "parent_code": "admin.roles.view",
    },
    {
        "perm_code": "admin.roles.delete",
        "perm_name": "删除角色",
        "perm_type": 2,
        "path": "/roles/{id}",
        "method": "DELETE",
        "parent_code": "admin.roles.view",
    },
    {
        "perm_code": "admin.roles.assign_permissions",
        "perm_name": "分配角色权限",
        "perm_type": 2,
        "path": "/roles/{id}/permissions",
        "method": "POST",
        "parent_code": "admin.roles.view",
    },
    {
        "perm_code": "admin.permissions.view",
        "perm_name": "查看权限",
        "perm_type": 1,
        "path": "/permissions",
        "method": "GET",
        "parent_code": None,
    },
    {
        "perm_code": "admin.permissions.create",
        "perm_name": "创建权限",
        "perm_type": 2,
        "path": "/permissions",
        "method": "POST",
        "parent_code": "admin.permissions.view",
    },
    {
        "perm_code": "admin.permissions.update",
        "perm_name": "更新权限",
        "perm_type": 2,
        "path": "/permissions/{id}",
        "method": "PUT",
        "parent_code": "admin.permissions.view",
    },
    {
        "perm_code": "admin.permissions.delete",
        "perm_name": "删除权限",
        "perm_type": 2,
        "path": "/permissions/{id}",
        "method": "DELETE",
        "parent_code": "admin.permissions.view",
    },
    {
        "perm_code": "admin.audit_logs.view",
        "perm_name": "查看审计日志",
        "perm_type": 1,
        "path": "/audit-logs",
        "method": "GET",
        "parent_code": None,
    },
]


async def seed_permissions(db) -> list[AdminPermission]:
    code_to_perm: dict[str, AdminPermission] = {}

    # 先按 perm_code 做幂等插入/更新
    for item in DEFAULT_PERMISSIONS:
        result = await db.execute(
            select(AdminPermission).where(AdminPermission.perm_code == item["perm_code"])
        )
        perm = result.scalar_one_or_none()
        if perm is None:
            perm = AdminPermission(
                perm_code=item["perm_code"],
                perm_name=item["perm_name"],
                perm_type=item["perm_type"],
                path=item["path"],
                method=item["method"],
                parent_id=0,
            )
            db.add(perm)
            await db.flush()
        else:
            perm.perm_name = item["perm_name"]
            perm.perm_type = item["perm_type"]
            perm.path = item["path"]
            perm.method = item["method"]

        code_to_perm[item["perm_code"]] = perm

    # 再回填 parent_id，避免父节点尚未创建
    for item in DEFAULT_PERMISSIONS:
        parent_code = item["parent_code"]
        perm = code_to_perm[item["perm_code"]]
        if parent_code is None:
            perm.parent_id = 0
        else:
            perm.parent_id = code_to_perm[parent_code].id

    await db.flush()
    return list(code_to_perm.values())


async def seed_role(db, permissions: list[AdminPermission]) -> AdminRole:
    role_code = os.getenv("INIT_ADMIN_ROLE_CODE", "super_admin")
    role_name = os.getenv("INIT_ADMIN_ROLE_NAME", "超级管理员")

    result = await db.execute(select(AdminRole).where(AdminRole.role_code == role_code))
    role = result.scalar_one_or_none()

    if role is None:
        role = AdminRole(
            role_code=role_code,
            role_name=role_name,
            is_system=1,
            status=1,
        )
        db.add(role)
        await db.flush()
    else:
        role.role_name = role_name
        role.is_system = 1
        role.status = 1

    # 避免 AsyncSession 下关系懒加载，直接维护关联表
    await db.execute(
        admin_role_permission.delete().where(admin_role_permission.c.role_id == role.id)
    )
    for perm in permissions:
        await db.execute(
            admin_role_permission.insert().values(role_id=role.id, permission_id=perm.id)
        )

    await db.flush()
    return role


async def seed_admin(db, role: AdminRole) -> AdminAccount:
    username = os.getenv("INIT_ADMIN_USERNAME", "admin")
    password = os.getenv("INIT_ADMIN_PASSWORD", "Admin@123456")
    real_name = os.getenv("INIT_ADMIN_REAL_NAME", "System Admin")
    force_reset = os.getenv("INIT_ADMIN_FORCE_RESET_PASSWORD", "false").lower() == "true"

    result = await db.execute(
        select(AdminAccount)
        .where(AdminAccount.username == username)
    )
    admin = result.scalar_one_or_none()

    if admin is None:
        admin = AdminAccount(
            username=username,
            password_hash=hash_password(password),
            real_name=real_name,
            status=1,
            created_by=None,
        )
        db.add(admin)
        await db.flush()
    else:
        admin.real_name = real_name
        admin.status = 1
        if force_reset:
            admin.password_hash = hash_password(password)

    role_link = await db.execute(
        select(admin_account_role).where(
            admin_account_role.c.admin_id == admin.id,
            admin_account_role.c.role_id == role.id,
        )
    )
    if role_link.first() is None:
        await db.execute(
            admin_account_role.insert().values(admin_id=admin.id, role_id=role.id)
        )

    await db.flush()
    return admin


async def run_seed() -> None:
    async with AsyncSessionLocal() as db:
        try:
            permissions = await seed_permissions(db)
            role = await seed_role(db, permissions)
            admin = await seed_admin(db, role)
            await db.commit()
            print(
                f"[seed] done: admin={admin.username}, role={role.role_code}, permissions={len(permissions)}"
            )
        except Exception:
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(run_seed())
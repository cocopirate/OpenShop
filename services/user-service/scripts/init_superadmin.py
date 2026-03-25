#!/usr/bin/env python3
"""
系统初始化脚本：创建超级管理员账号、角色及全量权限。
幂等执行，可重复运行，已存在的数据不会重复写入。

用法：
    # 使用默认账号 admin / Admin@123
    python scripts/init_superadmin.py

    # 自定义账号和密码（推荐生产环境使用）
    ADMIN_USERNAME=myuser ADMIN_PASSWORD=MyP@ss123 python scripts/init_superadmin.py
"""
from __future__ import annotations

import asyncio
import os
import sys

# 把项目根目录加入 sys.path，使 app.* 可以正常 import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
import bcrypt as _bcrypt

from app.core.config import settings
from app.models.permission import PermissionType


def _hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()

# ── 初始权限清单（与 API Gateway PERMISSION_MAP 保持一致）─────────────────
INITIAL_PERMISSIONS: list[dict] = [
    {"code": "*",                 "name": "超级权限（所有）",  "type": PermissionType.api.value,  "method": None,     "path": None},
    {"code": "user:list",         "name": "用户列表",          "type": PermissionType.api.value,  "method": "GET",    "path": "/api/users"},
    {"code": "user:create",       "name": "创建用户",          "type": PermissionType.api.value,  "method": "POST",   "path": "/api/users"},
    {"code": "user:update",       "name": "编辑用户",          "type": PermissionType.api.value,  "method": "PUT",    "path": "/api/users"},
    {"code": "user:delete",       "name": "删除用户",          "type": PermissionType.api.value,  "method": "DELETE", "path": "/api/users"},
    {"code": "role:list",         "name": "角色列表",          "type": PermissionType.api.value,  "method": "GET",    "path": "/api/roles"},
    {"code": "role:create",       "name": "创建角色",          "type": PermissionType.api.value,  "method": "POST",   "path": "/api/roles"},
    {"code": "role:update",       "name": "编辑角色",          "type": PermissionType.api.value,  "method": "PUT",    "path": "/api/roles"},
    {"code": "role:delete",       "name": "删除角色",          "type": PermissionType.api.value,  "method": "DELETE", "path": "/api/roles"},
    {"code": "permission:list",   "name": "权限列表",          "type": PermissionType.api.value,  "method": "GET",    "path": "/api/permissions"},
    {"code": "permission:create", "name": "创建权限",          "type": PermissionType.api.value,  "method": "POST",   "path": "/api/permissions"},
    {"code": "order:list",        "name": "订单列表",          "type": PermissionType.api.value,  "method": "GET",    "path": "/api/v1/orders"},
    {"code": "order:create",      "name": "创建订单",          "type": PermissionType.api.value,  "method": "POST",   "path": "/api/v1/orders"},
    {"code": "product:list",      "name": "商品列表",          "type": PermissionType.api.value,  "method": "GET",    "path": "/api/v1/products"},
    {"code": "product:create",    "name": "创建商品",          "type": PermissionType.api.value,  "method": "POST",   "path": "/api/v1/products"},
    {"code": "merchant:list",     "name": "商家列表",          "type": PermissionType.api.value,  "method": "GET",    "path": "/api/v1/merchants"},
    {"code": "merchant:create",   "name": "创建商家",          "type": PermissionType.api.value,  "method": "POST",   "path": "/api/v1/merchants"},
    {"code": "inventory:list",    "name": "库存列表",          "type": PermissionType.api.value,  "method": "GET",    "path": "/api/v1/inventory"},
    {"code": "promotion:list",    "name": "促销列表",          "type": PermissionType.api.value,  "method": "GET",    "path": "/api/v1/promotions"},
    {"code": "location:list",     "name": "地址列表",          "type": PermissionType.api.value,  "method": "GET",    "path": "/api/v1/locations"},
    {"code": "notification:send", "name": "发送通知",          "type": PermissionType.api.value,  "method": "POST",   "path": "/api/v1/notifications"},
]


async def init(username: str, password: str) -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    async with engine.begin() as conn:

        # ── Step 1：写入权限（ON CONFLICT DO NOTHING 保证幂等）──────────
        print("[ 1/4 ] 初始化权限...")
        for p in INITIAL_PERMISSIONS:
            result = await conn.execute(
                text("SELECT id FROM permissions WHERE code = :code"),
                {"code": p["code"]},
            )
            row = result.fetchone()
            if row is None:
                await conn.execute(
                    text(
                        "INSERT INTO permissions (code, name, type, method, path) "
                        "VALUES (:code, :name, :type, :method, :path)"
                    ),
                    p,
                )
                print(f"       [+] {p['code']}")
            else:
                print(f"       [=] {p['code']} (已存在)")

        # 获取 * 权限的 id
        star_id = (await conn.execute(
            text("SELECT id FROM permissions WHERE code = '*'")
        )).scalar_one()

        # ── Step 2：创建 superadmin 角色 ─────────────────────────────────
        print("[ 2/4 ] 初始化角色...")
        role_row = (await conn.execute(
            text("SELECT id FROM roles WHERE name = 'superadmin'")
        )).fetchone()

        if role_row is None:
            role_id = (await conn.execute(
                text(
                    "INSERT INTO roles (name, \"desc\") VALUES ('superadmin', '超级管理员，拥有所有权限') "
                    "RETURNING id"
                )
            )).scalar_one()
            print("       [+] 角色: superadmin")
        else:
            role_id = role_row[0]
            print("       [=] 角色 superadmin 已存在")

        # ── Step 3：角色绑定 * 权限 ───────────────────────────────────────
        print("[ 3/4 ] 绑定权限到角色...")
        rp_exists = (await conn.execute(
            text("SELECT 1 FROM role_permissions WHERE role_id = :rid AND permission_id = :pid"),
            {"rid": role_id, "pid": star_id},
        )).fetchone()

        if rp_exists is None:
            await conn.execute(
                text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:rid, :pid)"),
                {"rid": role_id, "pid": star_id},
            )
            print("       [+] superadmin → * 权限")
        else:
            print("       [=] superadmin 已绑定 * 权限")

        # ── Step 4：创建超级管理员账号 ────────────────────────────────────
        print("[ 4/4 ] 初始化管理员账号...")
        user_row = (await conn.execute(
            text("SELECT id FROM admin_users WHERE username = :username"),
            {"username": username},
        )).fetchone()

        if user_row is None:
            user_id = (await conn.execute(
                text(
                    "INSERT INTO admin_users (username, hashed_password, status) "
                    "VALUES (:username, :hashed_password, 'active') RETURNING id"
                ),
                {"username": username, "hashed_password": _hash_password(password)},
            )).scalar_one()
            print(f"       [+] 管理员账号: {username}")
        else:
            user_id = user_row[0]
            print(f"       [=] 账号 {username} 已存在")

        ur_exists = (await conn.execute(
            text("SELECT 1 FROM admin_user_roles WHERE admin_user_id = :uid AND role_id = :rid"),
            {"uid": user_id, "rid": role_id},
        )).fetchone()

        if ur_exists is None:
            await conn.execute(
                text("INSERT INTO admin_user_roles (admin_user_id, role_id) VALUES (:uid, :rid)"),
                {"uid": user_id, "rid": role_id},
            )
            print(f"       [+] {username} → superadmin 角色")
        else:
            print(f"       [=] {username} 已绑定 superadmin 角色")

    await engine.dispose()


def main() -> None:
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "Admin@123")

    print("=" * 52)
    print("  OpenShop 超级管理员初始化脚本")
    print("=" * 52)
    db_host = settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL
    print(f"  数据库: {db_host}")
    print(f"  账号:   {username}")
    print()

    asyncio.run(init(username, password))

    print()
    print("=" * 52)
    print("  初始化完成！")
    print()
    print("  登录接口：POST /api/auth/admin/login")
    print(f"  账号：{username}")
    print(f"  密码：{password}")
    print()
    print("  ⚠️  生产环境请立即修改默认密码！")
    print("=" * 52)


if __name__ == "__main__":
    main()

# User Service - Admin RBAC 权限系统

Admin 后台用户 / 角色 / 权限管理服务，基于 JWT + Redis 实现实时鉴权。

## 服务简介 / Overview

本服务为 OpenShop 管理后台提供：

- 用户账户管理（CRUD、状态控制）
- 角色管理（CRUD、权限分配）
- 权限管理（菜单权限、按钮权限、接口权限）
- JWT 登录 / 登出，Redis 实时撤销

**技术栈**：FastAPI · SQLAlchemy · PostgreSQL · Redis · python-jose · passlib

---

## 架构设计 / Architecture

```
Client
  │
  ▼
API Gateway  ──── JWT 验证 / Redis 状态校验
  │
  ▼
User Service
  ├── PostgreSQL  (用户 / 角色 / 权限持久化)
  └── Redis       (用户状态 / 权限版本 / 权限缓存)
```

RBAC 模型：

```
User ──(user_roles)──▶ Role ──(role_permissions)──▶ Permission
```

---

## 数据模型 / Data Models

### User

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| username | VARCHAR | 唯一用户名 |
| hashed_password | VARCHAR | bcrypt 哈希密码 |
| status | ENUM | active / disabled |
| created_at | TIMESTAMP | 创建时间 |

### Role

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | VARCHAR | 角色名称（唯一） |
| desc | TEXT | 角色描述 |
| created_at | TIMESTAMP | 创建时间 |

### Permission

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| code | VARCHAR | 权限码（唯一） |
| name | VARCHAR | 权限名称 |
| type | ENUM | menu / button / api |
| method | VARCHAR | HTTP 方法（GET/POST…） |
| path | VARCHAR | 路由路径 |
| parent_id | UUID | 父权限 ID（可空） |
| created_at | TIMESTAMP | 创建时间 |

### 关联表

- **user_roles** — (user_id, role_id)
- **role_permissions** — (role_id, permission_id)

---

## 鉴权方案 / Authentication Design

### JWT Payload

```json
{
  "uid": "用户ID",
  "username": "用户名",
  "roles": ["admin", "editor"],
  "permissions": ["user:list", "user:create"],
  "status": "active",
  "ver": 3,
  "exp": 1700000000
}
```

| 字段 | 说明 |
|------|------|
| uid | 用户 ID |
| username | 用户名 |
| roles | 角色列表 |
| permissions | 权限码列表 |
| status | 账号状态 |
| ver | 权限版本号（用于实时撤销） |
| exp | 过期时间 |

### Redis Key 设计

| Key | 说明 |
|-----|------|
| `user_status:{uid}` | 用户状态（active/disabled），账号禁用立即生效 |
| `user_perm_ver:{uid}` | 权限版本号，变更权限时 +1 |
| `user_permissions:{uid}` | 权限列表缓存（JSON），减少 DB 查询 |

### 鉴权流程

1. 客户端携带 `Authorization: Bearer <token>` 请求 API Gateway
2. Gateway 解码 JWT，取 `uid`、`ver`
3. 查询 `user_status:{uid}`：若为 `disabled` → 401
4. 查询 `user_perm_ver:{uid}`：若与 token `ver` 不符 → 401
5. 比对 `permissions` 与当前路由 → 无权限 → 403
6. 转发请求至 User Service

---

## API 接口 / API Reference

### 认证 Auth

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录获取 Token |
| POST | `/api/auth/logout` | 登出（Redis 清除状态） |

### 用户管理 User Management

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/users` | 获取用户列表 |
| POST | `/api/users` | 创建用户 |
| GET | `/api/users/{id}` | 获取用户详情 |
| PUT | `/api/users/{id}` | 更新用户 |
| DELETE | `/api/users/{id}` | 删除用户 |
| POST | `/api/users/{id}/status` | 修改用户状态 |
| POST | `/api/users/{id}/roles` | 分配角色 |

### 角色管理 Role Management

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/roles` | 获取角色列表 |
| POST | `/api/roles` | 创建角色 |
| GET | `/api/roles/{id}` | 获取角色详情 |
| PUT | `/api/roles/{id}` | 更新角色 |
| DELETE | `/api/roles/{id}` | 删除角色 |
| POST | `/api/roles/{id}/permissions` | 分配权限 |

### 权限管理 Permission Management

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/permissions` | 获取权限列表 |
| POST | `/api/permissions` | 创建权限 |
| GET | `/api/permissions/{id}` | 获取权限详情 |
| PUT | `/api/permissions/{id}` | 更新权限 |
| DELETE | `/api/permissions/{id}` | 删除权限 |

---

## 权限实时生效机制 / Real-time Permission Updates

### perm_ver 机制

每次修改用户角色或角色权限时，服务将 Redis 中该用户的 `user_perm_ver:{uid}` 自增 1。

```python
# 权限变更时使旧 Token 失效
redis.incr(f"user_perm_ver:{uid}")
redis.delete(f"user_permissions:{uid}")  # 清除权限缓存
```

Gateway 在每次请求时对比 Token 中的 `ver` 与 Redis 中的版本号，不一致则返回 401，强制用户重新登录并获取包含最新权限的新 Token。

### 用户禁用流程

```
管理员调用 POST /api/users/{id}/status {"status": "disabled"}
  │
  ▼
DB 更新 users.status = 'disabled'
  │
  ▼
Redis SET user_status:{uid} "disabled"
  │
  ▼
所有携带该用户 Token 的请求 → Gateway 检测 → 立即返回 401
```

---

## 目录结构 / Directory Structure

```
user-service/
├── app/
│   ├── api/v1/           # API 路由
│   │   ├── auth.py       # 认证接口
│   │   ├── users.py      # 用户管理
│   │   ├── roles.py      # 角色管理
│   │   └── permissions.py # 权限管理
│   ├── core/             # 核心模块
│   │   ├── config.py     # 配置
│   │   ├── database.py   # 数据库
│   │   ├── redis.py      # Redis
│   │   └── security.py   # JWT + 密码
│   ├── models/           # SQLAlchemy 数据模型
│   ├── schemas/          # Pydantic 模型
│   └── services/         # 业务逻辑
├── alembic/              # 数据库迁移
└── tests/                # 单元测试
```

---

## 快速开始 / Quick Start

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 复制环境变量
cp .env.example .env

# 3. 执行数据库迁移
alembic upgrade head

# 4. 启动服务
uvicorn app.main:app --reload --port 8001
```

---

## 测试 / Testing

```bash
pytest tests/ -v
```

---

## 安全说明 / Security Notes

- **密码**：bcrypt 哈希存储，明文密码不落库
- **JWT**：HS256 签名，过期时间可配置（默认 30 分钟）
- **实时撤销**：通过 Redis perm_ver 机制，权限变更后旧 Token 立即失效
- **用户状态**：每次请求均通过 Redis 校验用户状态，禁用账户立即阻断所有请求

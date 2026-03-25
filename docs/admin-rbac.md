# Admin RBAC 权限系统设计文档

> OpenShop 管理后台 — 基于角色的访问控制（RBAC）完整技术设计

---

## 1. 设计目标

1. **细粒度权限控制**：支持菜单、按钮、接口三级权限，满足复杂后台管控需求
2. **角色复用**：通过角色中间层，避免权限与用户直接绑定，降低维护成本
3. **实时生效**：权限或状态变更后，无需等待 Token 过期，立即对所有在线会话生效
4. **高性能鉴权**：JWT 无状态 + Redis 热数据缓存，鉴权链路不走数据库
5. **安全可靠**：密码 bcrypt 哈希，Token HS256 签名，版本号防重放
6. **易于扩展**：模型预留多租户、超级管理员、数据权限等扩展点

---

## 2. 系统架构

```
┌──────────┐     HTTP/HTTPS      ┌─────────────┐
│  Client  │ ──────────────────▶ │ API Gateway │
└──────────┘                     └──────┬──────┘
                                        │ 转发（已鉴权）
                                        ▼
                                 ┌─────────────┐
                                 │ User Service│
                                 └──────┬──────┘
                          ┌────────────┼────────────┐
                          ▼            ▼            ▼
                     ┌─────────┐  ┌───────┐  ┌────────┐
                     │PostgreSQL│  │ Redis │  │Alembic │
                     │（持久化） │  │（缓存）│  │（迁移） │
                     └─────────┘  └───────┘  └────────┘
```

**鉴权职责分离**：

- **API Gateway** — 验证 JWT 签名、检查 Redis 用户状态与权限版本、路由权限匹配
- **User Service** — 提供用户 / 角色 / 权限的 CRUD，变更时同步更新 Redis

---

## 3. RBAC 模型设计

### 实体关系

```
User ──┐
       ├──(user_roles)──▶ Role ──(role_permissions)──▶ Permission
       └── status (active/disabled)
```

### 数据表定义

#### users

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 用户 ID |
| username | VARCHAR(64) | UNIQUE, NOT NULL | 登录用户名 |
| hashed_password | VARCHAR(128) | NOT NULL | bcrypt 哈希密码 |
| status | ENUM('active','disabled') | DEFAULT 'active' | 账号状态 |
| created_at | TIMESTAMP | DEFAULT now() | 创建时间 |

#### roles

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 角色 ID |
| name | VARCHAR(64) | UNIQUE, NOT NULL | 角色名称 |
| desc | TEXT | | 角色描述 |
| created_at | TIMESTAMP | DEFAULT now() | 创建时间 |

#### permissions

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 权限 ID |
| code | VARCHAR(128) | UNIQUE, NOT NULL | 权限码，如 `user:create` |
| name | VARCHAR(64) | NOT NULL | 权限名称 |
| type | ENUM('menu','button','api') | NOT NULL | 权限类型 |
| method | VARCHAR(16) | | HTTP 方法（api 类型时必填） |
| path | VARCHAR(256) | | 路由路径（api 类型时必填） |
| parent_id | UUID | FK → permissions.id | 父权限（树形结构） |
| created_at | TIMESTAMP | DEFAULT now() | 创建时间 |

#### user_roles（关联表）

| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | UUID FK | 用户 ID |
| role_id | UUID FK | 角色 ID |

#### role_permissions（关联表）

| 字段 | 类型 | 说明 |
|------|------|------|
| role_id | UUID FK | 角色 ID |
| permission_id | UUID FK | 权限 ID |

---

## 4. JWT 设计

### Payload 格式

```json
{
  "uid": "550e8400-e29b-41d4-a716-446655440000",
  "username": "alice",
  "roles": ["admin", "editor"],
  "permissions": ["user:list", "user:create", "role:list"],
  "status": "active",
  "ver": 5,
  "exp": 1700001800
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| uid | string | 用户 UUID，Redis 查询主键 |
| username | string | 用户名，日志追踪用 |
| roles | string[] | 角色列表，前端菜单渲染 |
| permissions | string[] | 权限码列表，Gateway 鉴权 |
| status | string | 登录时快照，最终以 Redis 为准 |
| ver | int | 权限版本号，与 Redis `user_perm_ver:{uid}` 对比 |
| exp | int | Unix 时间戳，默认 30 分钟后过期 |

**签名算法**：HS256，密钥通过环境变量 `SECRET_KEY` 注入，不硬编码。

---

## 5. Redis 实时控制方案

### Key 设计

| Key 模式 | 类型 | TTL | 说明 |
|----------|------|-----|------|
| `user_status:{uid}` | String | 永久 / 随账号生命周期 | 账号状态：`active` 或 `disabled` |
| `user_perm_ver:{uid}` | String | 永久 | 权限版本计数器，整数 |
| `user_permissions:{uid}` | String (JSON) | 300s | 权限列表缓存，减少 DB 查询 |

### 鉴权校验伪代码（Gateway）

```python
async def auth_check(request, token):
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    uid = payload["uid"]
    ver = payload["ver"]

    # 1. 检查用户状态
    status = await redis.get(f"user_status:{uid}")
    if status == "disabled":
        raise HTTPException(401, "账号已禁用")

    # 2. 检查权限版本
    redis_ver = await redis.get(f"user_perm_ver:{uid}")
    if redis_ver and int(redis_ver) != ver:
        raise HTTPException(401, "权限已变更，请重新登录")

    # 3. 检查路由权限
    required = f"{request.method}:{request.path}"
    if required not in payload["permissions"]:
        raise HTTPException(403, "无访问权限")
```

### 权限变更流程

```
管理员修改角色权限
  │
  ▼
DB: 更新 role_permissions
  │
  ▼
对该角色下所有用户：
  redis.incr("user_perm_ver:{uid}")      # 版本号 +1
  redis.delete("user_permissions:{uid}") # 清除缓存
  │
  ▼
用户下次请求 → Gateway ver 校验失败 → 401 → 重新登录
新 Token 携带最新权限版本和权限列表
```

### 用户禁用流程

```
POST /api/users/{id}/status  {"status": "disabled"}
  │
  ▼
DB: UPDATE users SET status='disabled'
  │
  ▼
Redis: SET user_status:{uid} "disabled"
  │
  ▼
该用户所有在线会话下次请求 → 401（立即生效，无需等 Token 过期）
```

---

## 6. API 设计

### 认证模块 `/api/auth`

| 方法 | 路径 | 请求体 | 响应 | 说明 |
|------|------|--------|------|------|
| POST | `/api/auth/login` | `{username, password}` | `{token, expires_in}` | 登录获取 JWT |
| POST | `/api/auth/logout` | — | `{message}` | 登出，清理 Redis 状态 |

### 用户模块 `/api/users`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/users` | 获取用户列表（分页、搜索） |
| POST | `/api/users` | 创建用户 |
| GET | `/api/users/{id}` | 获取用户详情（含角色） |
| PUT | `/api/users/{id}` | 更新用户基本信息 |
| DELETE | `/api/users/{id}` | 删除用户 |
| POST | `/api/users/{id}/status` | 修改用户状态（active/disabled） |
| POST | `/api/users/{id}/roles` | 覆盖分配角色列表 |

### 角色模块 `/api/roles`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/roles` | 获取角色列表 |
| POST | `/api/roles` | 创建角色 |
| GET | `/api/roles/{id}` | 获取角色详情（含权限） |
| PUT | `/api/roles/{id}` | 更新角色信息 |
| DELETE | `/api/roles/{id}` | 删除角色 |
| POST | `/api/roles/{id}/permissions` | 覆盖分配权限列表 |

### 权限模块 `/api/permissions`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/permissions` | 获取权限列表（树形 / 平铺） |
| POST | `/api/permissions` | 创建权限 |
| GET | `/api/permissions/{id}` | 获取权限详情 |
| PUT | `/api/permissions/{id}` | 更新权限 |
| DELETE | `/api/permissions/{id}` | 删除权限 |

---

## 7. 缓存与性能设计

### 缓存策略

| 数据 | 缓存键 | TTL | 更新时机 |
|------|--------|-----|----------|
| 用户权限列表 | `user_permissions:{uid}` | 300s | 角色/权限变更时主动删除 |
| 用户状态 | `user_status:{uid}` | 永久 | 状态变更时主动写入 |
| 权限版本 | `user_perm_ver:{uid}` | 永久 | 权限变更时 incr |

### 缓存更新策略对比

| 策略 | 适用场景 | 本项目选择 |
|------|----------|-----------|
| 旁路缓存（Cache Aside） | 读多写少 | ✅ 权限列表缓存 |
| 主动失效（Write Through） | 强一致性要求 | ✅ 用户状态 / 版本号 |
| TTL 自然过期 | 允许短暂不一致 | ✅ 权限缓存兜底 |

---

## 8. 安全设计要点

### 密码安全

- 使用 `passlib[bcrypt]` 哈希存储，cost factor 默认 12
- 登录接口使用恒定时间比较，防时序攻击
- 禁止在日志、响应体中输出明文或哈希密码

### JWT 安全

- 密钥通过环境变量注入，不硬编码进源码
- 算法固定为 HS256，拒绝 `none` 算法
- 短期 Token（默认 30 分钟）+ Redis 实时撤销双重保障
- Token 仅在 `Authorization: Bearer` 头传递，不放 URL 参数

### 防权限提升

- 分配角色 / 权限接口需校验操作者自身权限
- 普通管理员不能给自己分配超出自身角色范围的权限
- 删除角色时检查是否仍有用户绑定，防止遗漏清理

---

## 9. 扩展设计

### 多租户

在 User / Role / Permission 表增加 `tenant_id` 字段，所有查询默认过滤当前租户，实现租户间数据隔离。

### 超级管理员

在 JWT Payload 增加 `is_superadmin` 布尔字段，Gateway 对超级管理员跳过权限码校验，仅校验 Token 有效性。

### 数据权限

在 Permission 表增加 `data_scope` 字段（all / dept / self），配合请求上下文注入数据过滤条件，实现行级权限控制。

---

*文档版本：v1.0 | 最后更新：2024*

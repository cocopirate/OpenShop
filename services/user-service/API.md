# User Service — 接口文档

**Base URL（直连）**: `http://localhost:8001`  
**Base URL（经网关）**: `http://localhost:8080`  
**Content-Type**: `application/json`  
**认证方式**: `Authorization: Bearer <access_token>`

---

## 目录

1. [健康检查](#健康检查)
2. [认证 Auth](#认证-auth)
3. [管理员用户管理 AdminUser](#管理员用户管理-adminuser)
4. [角色管理 Role](#角色管理-role)
5. [权限管理 Permission](#权限管理-permission)

---

## 健康检查

### GET /health

服务存活检查，同时验证数据库与 Redis 连接。

**无需认证**

**请求示例**

```http
GET /health HTTP/1.1
Host: localhost:8001
```

**响应示例（200 OK）**

```json
{
  "status": "ok",
  "db": "ok",
  "redis": "ok"
}
```

---

### GET /health/ready

Kubernetes Readiness Probe，服务就绪后返回 200。

**无需认证**

**请求示例**

```http
GET /health/ready HTTP/1.1
Host: localhost:8001
```

**响应示例（200 OK）**

```json
{
  "status": "ready"
}
```

---

## 认证 Auth

### POST /api/auth/admin/login

管理员登录，成功后返回 JWT Access Token。

**无需认证**

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | ✓ | 管理员用户名 |
| password | string | ✓ | 明文密码 |

**请求示例**

```http
POST /api/auth/admin/login HTTP/1.1
Host: localhost:8001
Content-Type: application/json

{
  "username": "admin",
  "password": "Admin@123"
}
```

**响应示例（200 OK）**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOiI3YzE4MWQ3Yi00MjI0LTQxODktOTEzMi1mOWE4ZmM1OGEzNzMiLCJ1c2VybmFtZSI6ImFkbWluIiwicm9sZXMiOlsic3VwZXJhZG1pbiJdLCJwZXJtaXNzaW9ucyI6WyIqIl0sInN0YXR1cyI6ImFjdGl2ZSIsInZlciI6MCwiZXhwIjoxNzAwMDAxODAwfQ.example",
  "token_type": "bearer"
}
```

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 401 | 用户名或密码错误 |
| 403 | 账号已被禁用 |

---

### POST /api/auth/logout

登出当前账号。

**需要认证**

**请求示例**

```http
POST /api/auth/logout HTTP/1.1
Host: localhost:8001
Authorization: Bearer <access_token>
```

**响应示例（200 OK）**

```json
{
  "message": "logged out"
}
```

---

## 管理员用户管理 AdminUser

> 所有接口均需携带有效 JWT Token，且需要对应权限码。

### GET /api/users

获取所有管理员用户列表。

**所需权限**: `user:list`

**请求示例**

```http
GET /api/users HTTP/1.1
Host: localhost:8001
Authorization: Bearer <access_token>
```

**响应示例（200 OK）**

```json
[
  {
    "public_id": "7c181d7b-4224-4189-9132-f9a8fc58a373",
    "username": "admin",
    "status": "active",
    "created_at": "2024-01-01T00:00:00"
  },
  {
    "public_id": "a1b2c3d4-0000-0000-0000-000000000001",
    "username": "operator01",
    "status": "active",
    "created_at": "2024-01-02T08:30:00"
  }
]
```

---

### POST /api/users

创建新管理员用户。

**所需权限**: `user:create`

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | ✓ | 用户名（唯一） |
| password | string | ✓ | 明文密码（会被 bcrypt 哈希存储） |
| status | string | — | `active`（默认）或 `disabled` |

**请求示例**

```http
POST /api/users HTTP/1.1
Host: localhost:8001
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "username": "operator01",
  "password": "Operator@123",
  "status": "active"
}
```

**响应示例（201 Created）**

```json
{
  "public_id": "a1b2c3d4-0000-0000-0000-000000000001",
  "username": "operator01",
  "status": "active",
  "created_at": "2024-06-01T10:00:00"
}
```

---

### GET /api/users/{user_id}

获取指定管理员用户详情（`user_id` 为 UUID）。

**所需权限**: `user:list`

**请求示例**

```http
GET /api/users/7c181d7b-4224-4189-9132-f9a8fc58a373 HTTP/1.1
Host: localhost:8001
Authorization: Bearer <access_token>
```

**响应示例（200 OK）**

```json
{
  "public_id": "7c181d7b-4224-4189-9132-f9a8fc58a373",
  "username": "admin",
  "status": "active",
  "created_at": "2024-01-01T00:00:00"
}
```

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 404 | 用户不存在 |

---

### PUT /api/users/{user_id}

更新指定管理员用户信息（字段均为可选，仅传需修改的字段）。

**所需权限**: `user:update`

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | — | 新用户名 |
| status | string | — | `active` 或 `disabled` |

**请求示例**

```http
PUT /api/users/7c181d7b-4224-4189-9132-f9a8fc58a373 HTTP/1.1
Host: localhost:8001
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "username": "admin_renamed"
}
```

**响应示例（200 OK）**

```json
{
  "public_id": "7c181d7b-4224-4189-9132-f9a8fc58a373",
  "username": "admin_renamed",
  "status": "active",
  "created_at": "2024-01-01T00:00:00"
}
```

---

### DELETE /api/users/{user_id}

删除指定管理员用户。

**所需权限**: `user:delete`

**请求示例**

```http
DELETE /api/users/a1b2c3d4-0000-0000-0000-000000000001 HTTP/1.1
Host: localhost:8001
Authorization: Bearer <access_token>
```

**响应示例（200 OK）**

```json
{
  "message": "deleted"
}
```

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 404 | 用户不存在 |

---

### POST /api/users/{user_id}/status

启用或禁用指定管理员用户账号。禁用后 Redis 中对应状态立即生效，该用户后续所有请求将被网关拦截（401）。

**所需权限**: `user:update`

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | ✓ | `active` 或 `disabled` |

**请求示例（禁用账号）**

```http
POST /api/users/a1b2c3d4-0000-0000-0000-000000000001/status HTTP/1.1
Host: localhost:8001
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "status": "disabled"
}
```

**响应示例（200 OK）**

```json
{
  "public_id": "a1b2c3d4-0000-0000-0000-000000000001",
  "username": "operator01",
  "status": "disabled",
  "created_at": "2024-06-01T10:00:00"
}
```

---

### POST /api/users/{user_id}/roles

为指定管理员用户批量分配角色（全量覆盖，传空数组则清空所有角色）。分配后 Redis 权限版本号自增，旧 Token 立即失效。

**所需权限**: `user:update`

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| role_ids | array[int] | ✓ | 角色 ID 列表 |

**请求示例**

```http
POST /api/users/a1b2c3d4-0000-0000-0000-000000000001/roles HTTP/1.1
Host: localhost:8001
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "role_ids": [1, 2]
}
```

**响应示例（200 OK）**

```json
{
  "public_id": "a1b2c3d4-0000-0000-0000-000000000001",
  "username": "operator01",
  "status": "active",
  "created_at": "2024-06-01T10:00:00"
}
```

---

## 角色管理 Role

### GET /api/roles

获取所有角色列表。

**所需权限**: `role:list`

**请求示例**

```http
GET /api/roles HTTP/1.1
Host: localhost:8001
Authorization: Bearer <access_token>
```

**响应示例（200 OK）**

```json
[
  {
    "id": 1,
    "name": "superadmin",
    "desc": "超级管理员，拥有全部权限",
    "created_at": "2024-01-01T00:00:00"
  },
  {
    "id": 2,
    "name": "operator",
    "desc": "运营人员，拥有商品和订单读取权限",
    "created_at": "2024-01-02T00:00:00"
  }
]
```

---

### POST /api/roles

创建新角色。

**所需权限**: `role:create`

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ✓ | 角色名称（唯一） |
| desc | string | — | 角色描述 |

**请求示例**

```http
POST /api/roles HTTP/1.1
Host: localhost:8001
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "operator",
  "desc": "运营人员，拥有商品和订单读取权限"
}
```

**响应示例（201 Created）**

```json
{
  "id": 2,
  "name": "operator",
  "desc": "运营人员，拥有商品和订单读取权限",
  "created_at": "2024-06-01T10:00:00"
}
```

---

### GET /api/roles/{role_id}

获取指定角色详情。

**所需权限**: `role:list`

**请求示例**

```http
GET /api/roles/1 HTTP/1.1
Host: localhost:8001
Authorization: Bearer <access_token>
```

**响应示例（200 OK）**

```json
{
  "id": 1,
  "name": "superadmin",
  "desc": "超级管理员，拥有全部权限",
  "created_at": "2024-01-01T00:00:00"
}
```

---

### PUT /api/roles/{role_id}

更新角色信息。

**所需权限**: `role:update`

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | — | 新角色名 |
| desc | string | — | 新描述 |

**请求示例**

```http
PUT /api/roles/2 HTTP/1.1
Host: localhost:8001
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "desc": "运营人员（更新描述）"
}
```

**响应示例（200 OK）**

```json
{
  "id": 2,
  "name": "operator",
  "desc": "运营人员（更新描述）",
  "created_at": "2024-01-02T00:00:00"
}
```

---

### DELETE /api/roles/{role_id}

删除指定角色。

**所需权限**: `role:delete`

**请求示例**

```http
DELETE /api/roles/2 HTTP/1.1
Host: localhost:8001
Authorization: Bearer <access_token>
```

**响应示例（200 OK）**

```json
{
  "message": "deleted"
}
```

---

### POST /api/roles/{role_id}/permissions

为指定角色批量分配权限（全量覆盖）。分配后，持有该角色的所有管理员用户的 Redis 权限版本号自增，旧 Token 立即失效。

**所需权限**: `role:update`

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| permission_ids | array[int] | ✓ | 权限 ID 列表 |

**请求示例**

```http
POST /api/roles/2/permissions HTTP/1.1
Host: localhost:8001
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "permission_ids": [1, 2, 3]
}
```

**响应示例（200 OK）**

```json
{
  "id": 2,
  "name": "operator",
  "desc": "运营人员，拥有商品和订单读取权限",
  "created_at": "2024-01-02T00:00:00"
}
```

---

## 权限管理 Permission

### GET /api/permissions

获取所有权限列表。

**所需权限**: `permission:list`

**请求示例**

```http
GET /api/permissions HTTP/1.1
Host: localhost:8001
Authorization: Bearer <access_token>
```

**响应示例（200 OK）**

```json
[
  {
    "id": 1,
    "code": "user:list",
    "name": "查看管理员用户",
    "type": "api",
    "method": "GET",
    "path": "/api/users",
    "parent_id": null,
    "created_at": "2024-01-01T00:00:00"
  },
  {
    "id": 2,
    "code": "user:create",
    "name": "创建管理员用户",
    "type": "api",
    "method": "POST",
    "path": "/api/users",
    "parent_id": null,
    "created_at": "2024-01-01T00:00:00"
  },
  {
    "id": 3,
    "code": "dashboard",
    "name": "仪表盘菜单",
    "type": "menu",
    "method": null,
    "path": null,
    "parent_id": null,
    "created_at": "2024-01-01T00:00:00"
  }
]
```

---

### POST /api/permissions

创建新权限。

**所需权限**: `permission:create`

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code | string | ✓ | 权限码（唯一），如 `user:list` |
| name | string | ✓ | 权限名称 |
| type | string | ✓ | `menu`（菜单权限）或 `api`（接口权限） |
| method | string | — | HTTP 方法，`type=api` 时填写（GET/POST/PUT/DELETE） |
| path | string | — | 路由路径，`type=api` 时填写，如 `/api/users` |
| parent_id | int | — | 父权限 ID（用于层级菜单） |

**请求示例（API 类型权限）**

```http
POST /api/permissions HTTP/1.1
Host: localhost:8001
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "code": "report:view",
  "name": "查看报表",
  "type": "api",
  "method": "GET",
  "path": "/api/v1/reports"
}
```

**请求示例（菜单类型权限）**

```http
POST /api/permissions HTTP/1.1
Host: localhost:8001
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "code": "dashboard",
  "name": "仪表盘菜单",
  "type": "menu"
}
```

**响应示例（201 Created）**

```json
{
  "id": 10,
  "code": "report:view",
  "name": "查看报表",
  "type": "api",
  "method": "GET",
  "path": "/api/v1/reports",
  "parent_id": null,
  "created_at": "2024-06-01T10:00:00"
}
```

---

### GET /api/permissions/{perm_id}

获取指定权限详情。

**所需权限**: `permission:list`

**请求示例**

```http
GET /api/permissions/1 HTTP/1.1
Host: localhost:8001
Authorization: Bearer <access_token>
```

**响应示例（200 OK）**

```json
{
  "id": 1,
  "code": "user:list",
  "name": "查看管理员用户",
  "type": "api",
  "method": "GET",
  "path": "/api/users",
  "parent_id": null,
  "created_at": "2024-01-01T00:00:00"
}
```

---

### PUT /api/permissions/{perm_id}

更新指定权限（字段均为可选）。

**所需权限**: `permission:update`

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code | string | — | 新权限码 |
| name | string | — | 新权限名 |
| type | string | — | `menu` 或 `api` |
| method | string | — | 新 HTTP 方法 |
| path | string | — | 新路由路径 |
| parent_id | int | — | 新父权限 ID |

**请求示例**

```http
PUT /api/permissions/10 HTTP/1.1
Host: localhost:8001
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "查看所有报表"
}
```

**响应示例（200 OK）**

```json
{
  "id": 10,
  "code": "report:view",
  "name": "查看所有报表",
  "type": "api",
  "method": "GET",
  "path": "/api/v1/reports",
  "parent_id": null,
  "created_at": "2024-06-01T10:00:00"
}
```

---

### DELETE /api/permissions/{perm_id}

删除指定权限。

**所需权限**: `permission:delete`

**请求示例**

```http
DELETE /api/permissions/10 HTTP/1.1
Host: localhost:8001
Authorization: Bearer <access_token>
```

**响应示例（200 OK）**

```json
{
  "message": "deleted"
}
```

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 404 | 权限不存在 |

---

## 通用错误码

| 状态码 | 说明 |
|--------|------|
| 400 | 请求参数校验失败（Pydantic 验证错误） |
| 401 | 未携带 Token、Token 无效/过期，或账号已禁用 |
| 403 | 账号已禁用（登录时）或缺少所需权限 |
| 404 | 资源不存在 |
| 422 | 请求体格式错误（FastAPI Unprocessable Entity） |
| 500 | 服务器内部错误 |

**401 响应示例**

```json
{
  "detail": "Token invalidated, please login again"
}
```

**403 响应示例**

```json
{
  "detail": "Missing permission: user:create"
}
```

**422 响应示例**

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "username"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

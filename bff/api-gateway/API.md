# API Gateway — 接口文档

**网关地址**: `http://localhost:8080`  
**Content-Type**: `application/json`  
**认证方式**: `Authorization: Bearer <access_token>`

网关作为所有客户端流量的统一入口，负责 JWT 鉴权、路由转发、限流保护与请求日志记录。所有下游服务均通过网关对外暴露。

---

## 目录

1. [认证说明](#认证说明)
2. [路由规则](#路由规则)
3. [健康检查](#健康检查)
4. [认证 Auth（转发至 user-service）](#认证-auth转发至-user-service)
5. [管理员用户管理（转发至 user-service）](#管理员用户管理转发至-user-service)
6. [角色管理（转发至 user-service）](#角色管理转发至-user-service)
7. [权限管理（转发至 user-service）](#权限管理转发至-user-service)
8. [通用错误码](#通用错误码)

---

## 认证说明

### 获取 Token

调用 `POST /api/auth/admin/login` 登录，响应体中的 `access_token` 即为 JWT Token。

后续请求在 HTTP Header 中携带：

```
Authorization: Bearer <access_token>
```

### Token 内容（JWT Payload）

```json
{
  "uid": "7c181d7b-4224-4189-9132-f9a8fc58a373",
  "username": "admin",
  "roles": ["superadmin"],
  "permissions": ["*"],
  "status": "active",
  "ver": 0,
  "exp": 1700001800
}
```

| 字段 | 说明 |
|------|------|
| uid | 用户唯一 ID（UUID） |
| username | 用户名 |
| roles | 角色列表 |
| permissions | 权限码列表（`*` 表示超级权限） |
| status | 账号状态（active / disabled） |
| ver | 权限版本号，用于实时撤销旧 Token |
| exp | 过期时间（Unix 时间戳） |

### 鉴权流程

```
客户端请求
    ↓
① 判断是否为公开路径（/api/auth/login、/health 等） → 跳过鉴权
    ↓
② 从 Authorization Header 提取 Bearer Token
    ↓
③ 验证 JWT 签名与过期时间
    ↓
④ 查询 Redis user_status:{uid} → disabled → 返回 401
    ↓
⑤ 对比 Token ver 与 Redis user_perm_ver:{uid} → 不一致 → 返回 401
    ↓
⑥ 根据 PERMISSION_MAP 校验当前路径权限 → 无权限 → 返回 403
    ↓
⑦ 转发请求至上游服务，将响应原样返回客户端
```

### 公开路径（无需鉴权）

| 方法 | 路径 |
|------|------|
| POST | /api/auth/login |
| POST | /api/auth/admin/login |
| GET | /health |
| GET | /health/ready |
| GET | /metrics |

### 限流规则

- 每分钟最多 **60** 次请求
- 每小时最多 **1000** 次请求

---

## 路由规则

网关按最长前缀匹配将请求转发到对应下游服务：

| 路径前缀 | 上游服务 | 端口 |
|---------|---------|------|
| `/api/auth/**` | user-service | 8001 |
| `/api/users/**` | user-service | 8001 |
| `/api/roles/**` | user-service | 8001 |
| `/api/permissions/**` | user-service | 8001 |
| `/api/v1/merchants/**` | merchant-service | 8002 |
| `/api/v1/products/**` | product-service | 8003 |
| `/api/v1/inventory/**` | inventory-service | 8004 |
| `/api/v1/orders/**` | order-service | 8005 |
| `/api/v1/aftersale/**` | aftersale-service | 8006 |
| `/api/v1/promotions/**` | promotion-service | 8007 |
| `/api/v1/locations/**` | location-service | 8008 |
| `/api/v1/notifications/**` | notification-service | 8009 |
| `/api/v1/sms/**` | sms-service | 8010 |

---

## 健康检查

### GET /health

网关自身健康检查，同时验证 Redis 连接。

**无需认证**

**请求示例**

```http
GET /health HTTP/1.1
Host: localhost:8080
```

```bash
curl http://localhost:8080/health
```

**响应示例（200 OK）**

```json
{
  "status": "ok",
  "redis": "ok"
}
```

---

### GET /health/ready

Kubernetes Readiness Probe。

**无需认证**

**请求示例**

```http
GET /health/ready HTTP/1.1
Host: localhost:8080
```

```bash
curl http://localhost:8080/health/ready
```

**响应示例（200 OK）**

```json
{
  "status": "ready"
}
```

---

## 认证 Auth（转发至 user-service）

### POST /api/auth/admin/login

管理员登录，返回 JWT Access Token。**无需认证。**

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | ✓ | 管理员用户名 |
| password | string | ✓ | 明文密码 |

**请求示例**

```http
POST /api/auth/admin/login HTTP/1.1
Host: localhost:8080
Content-Type: application/json

{
  "username": "admin",
  "password": "Admin@123"
}
```

```bash
curl -X POST \
  http://localhost:8080/api/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "Admin@123"}'
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
Host: localhost:8080
Authorization: Bearer <access_token>
```

```bash
curl -X POST \
  http://localhost:8080/api/auth/logout \
  -H "Authorization: Bearer <access_token>"
```

**响应示例（200 OK）**

```json
{
  "message": "logged out"
}
```

---

## 管理员用户管理（转发至 user-service）

### GET /api/users

获取管理员用户列表。

**所需权限**: `user:list`

**请求示例**

```http
GET /api/users HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
```

```bash
curl http://localhost:8080/api/users \
  -H "Authorization: Bearer <access_token>"
```

**响应示例（200 OK）**

```json
[
  {
    "public_id": "7c181d7b-4224-4189-9132-f9a8fc58a373",
    "username": "admin",
    "status": "active",
    "created_at": "2024-01-01T00:00:00"
  }
]
```

---

### POST /api/users

创建管理员用户。

**所需权限**: `user:create`

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | ✓ | 用户名（唯一） |
| password | string | ✓ | 明文密码 |
| status | string | — | `active`（默认）或 `disabled` |

**请求示例**

```http
POST /api/users HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "username": "operator01",
  "password": "Operator@123",
  "status": "active"
}
```

```bash
curl -X POST \
  http://localhost:8080/api/users \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"username": "operator01", "password": "Operator@123", "status": "active"}'
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
Host: localhost:8080
Authorization: Bearer <access_token>
```

```bash
curl http://localhost:8080/api/users/7c181d7b-4224-4189-9132-f9a8fc58a373 \
  -H "Authorization: Bearer <access_token>"
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

---

### PUT /api/users/{user_id}

更新管理员用户信息。

**所需权限**: `user:update`

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | — | 新用户名 |
| status | string | — | `active` 或 `disabled` |

**请求示例**

```http
PUT /api/users/7c181d7b-4224-4189-9132-f9a8fc58a373 HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "username": "admin_renamed"
}
```

```bash
curl -X PUT \
  http://localhost:8080/api/users/7c181d7b-4224-4189-9132-f9a8fc58a373 \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin_renamed"}'
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

删除管理员用户。

**所需权限**: `user:delete`

**请求示例**

```http
DELETE /api/users/a1b2c3d4-0000-0000-0000-000000000001 HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
```

```bash
curl -X DELETE \
  http://localhost:8080/api/users/a1b2c3d4-0000-0000-0000-000000000001 \
  -H "Authorization: Bearer <access_token>"
```

**响应示例（200 OK）**

```json
{
  "message": "deleted"
}
```

---

### POST /api/users/{user_id}/status

启用或禁用管理员账号，立即生效。

**所需权限**: `user:update`

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | ✓ | `active` 或 `disabled` |

**请求示例（禁用账号）**

```http
POST /api/users/a1b2c3d4-0000-0000-0000-000000000001/status HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "status": "disabled"
}
```

```bash
curl -X POST \
  http://localhost:8080/api/users/a1b2c3d4-0000-0000-0000-000000000001/status \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"status": "disabled"}'
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

为管理员用户批量分配角色（全量覆盖）。

**所需权限**: `user:update`

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| role_ids | array[int] | ✓ | 角色 ID 列表 |

**请求示例**

```http
POST /api/users/a1b2c3d4-0000-0000-0000-000000000001/roles HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "role_ids": [1, 2]
}
```

```bash
curl -X POST \
  http://localhost:8080/api/users/a1b2c3d4-0000-0000-0000-000000000001/roles \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"role_ids": [1, 2]}'
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

## 角色管理（转发至 user-service）

### GET /api/roles

获取所有角色列表。

**所需权限**: `role:list`

**请求示例**

```http
GET /api/roles HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
```

```bash
curl http://localhost:8080/api/roles \
  -H "Authorization: Bearer <access_token>"
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
    "desc": "运营人员",
    "created_at": "2024-01-02T00:00:00"
  }
]
```

---

### POST /api/roles

创建角色。

**所需权限**: `role:create`

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ✓ | 角色名（唯一） |
| desc | string | — | 角色描述 |

**请求示例**

```http
POST /api/roles HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "operator",
  "desc": "运营人员"
}
```

```bash
curl -X POST \
  http://localhost:8080/api/roles \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "operator", "desc": "运营人员"}'
```

**响应示例（201 Created）**

```json
{
  "id": 2,
  "name": "operator",
  "desc": "运营人员",
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
Host: localhost:8080
Authorization: Bearer <access_token>
```

```bash
curl http://localhost:8080/api/roles/1 \
  -H "Authorization: Bearer <access_token>"
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

更新角色。

**所需权限**: `role:update`

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | — | 新角色名 |
| desc | string | — | 新描述 |

**请求示例**

```http
PUT /api/roles/2 HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "desc": "运营人员（已更新描述）"
}
```

```bash
curl -X PUT \
  http://localhost:8080/api/roles/2 \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"desc": "运营人员（已更新描述）"}'
```

**响应示例（200 OK）**

```json
{
  "id": 2,
  "name": "operator",
  "desc": "运营人员（已更新描述）",
  "created_at": "2024-01-02T00:00:00"
}
```

---

### DELETE /api/roles/{role_id}

删除角色。

**所需权限**: `role:delete`

**请求示例**

```http
DELETE /api/roles/999 HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
```

```bash
curl -X DELETE \
  http://localhost:8080/api/roles/999 \
  -H "Authorization: Bearer <access_token>"
```

**响应示例（200 OK）**

```json
{
  "message": "deleted"
}
```

---

### POST /api/roles/{role_id}/permissions

为角色批量分配权限（全量覆盖）。

**所需权限**: `role:update`

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| permission_ids | array[int] | ✓ | 权限 ID 列表 |

**请求示例**

```http
POST /api/roles/2/permissions HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "permission_ids": [1, 2, 3]
}
```

```bash
curl -X POST \
  http://localhost:8080/api/roles/2/permissions \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"permission_ids": [1, 2, 3]}'
```

**响应示例（200 OK）**

```json
{
  "id": 2,
  "name": "operator",
  "desc": "运营人员",
  "created_at": "2024-01-02T00:00:00"
}
```

---

## 权限管理（转发至 user-service）

### GET /api/permissions

获取所有权限列表。

**所需权限**: `permission:list`

**请求示例**

```http
GET /api/permissions HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
```

```bash
curl http://localhost:8080/api/permissions \
  -H "Authorization: Bearer <access_token>"
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
  }
]
```

---

### POST /api/permissions

创建权限。

**所需权限**: `permission:create`

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code | string | ✓ | 权限码（唯一），如 `user:list` |
| name | string | ✓ | 权限名称 |
| type | string | ✓ | `menu` 或 `api` |
| method | string | — | HTTP 方法（`type=api` 时填写） |
| path | string | — | 路由路径（`type=api` 时填写） |
| parent_id | int | — | 父权限 ID |

**请求示例**

```http
POST /api/permissions HTTP/1.1
Host: localhost:8080
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

```bash
curl -X POST \
  http://localhost:8080/api/permissions \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"code": "report:view", "name": "查看报表", "type": "api", "method": "GET", "path": "/api/v1/reports"}'
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
Host: localhost:8080
Authorization: Bearer <access_token>
```

```bash
curl http://localhost:8080/api/permissions/1 \
  -H "Authorization: Bearer <access_token>"
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

更新权限。

**所需权限**: `permission:update`

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code | string | — | 新权限码 |
| name | string | — | 新名称 |
| type | string | — | `menu` 或 `api` |
| method | string | — | 新 HTTP 方法 |
| path | string | — | 新路由路径 |
| parent_id | int | — | 新父权限 ID |

**请求示例**

```http
PUT /api/permissions/10 HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "查看所有报表"
}
```

```bash
curl -X PUT \
  http://localhost:8080/api/permissions/10 \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "查看所有报表"}'
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

删除权限。

**所需权限**: `permission:delete`

**请求示例**

```http
DELETE /api/permissions/999 HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
```

```bash
curl -X DELETE \
  http://localhost:8080/api/permissions/999 \
  -H "Authorization: Bearer <access_token>"
```

**响应示例（200 OK）**

```json
{
  "message": "deleted"
}
```

---

## 通用错误码

| 状态码 | 说明 |
|--------|------|
| 400 | 请求参数校验失败 |
| 401 | 未认证、Token 无效/过期/被撤销，或账号已禁用 |
| 403 | 缺少所需权限 |
| 404 | 路径无匹配的上游服务，或资源不存在 |
| 422 | 请求体格式错误 |
| 503 | 上游服务不可用（连接失败） |
| 504 | 上游服务超时（默认 30s） |

**401 响应示例（Token 被撤销）**

```json
{
  "detail": "Token invalidated, please login again"
}
```

**401 响应示例（用户已禁用）**

```json
{
  "detail": "User is disabled"
}
```

**403 响应示例**

```json
{
  "detail": "Missing permission: user:create"
}
```

**503 响应示例**

```json
{
  "detail": "Upstream service unavailable"
}
```

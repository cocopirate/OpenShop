# Admin Service API 文档

Base URL：`http://localhost:8012`

所有响应均使用统一结构：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

| code | 含义 |
|------|------|
| 0 | 成功 |
| 40001 | 管理员不存在 |
| 40002 | 用户名已存在 |
| 40005 | 角色不存在 |
| 40006 | 权限不存在 |
| 40012 | 系统角色不可删除 |
| 40011 | 请求参数校验失败 |

---

## 管理员账号 Admins

### GET /admins

分页获取管理员列表。

**Query 参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | int | 1 | 页码 |
| page_size | int | 20 | 每页数量 |

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "public_id": "018e1b2c-3d4e-7f5a-8b9c-0d1e2f3a4b5c",
        "username": "admin",
        "real_name": "System Admin",
        "phone": null,
        "status": 1,
        "last_login_at": null,
        "last_login_ip": null,
        "created_by": null,
        "created_at": "2026-03-27T10:00:00"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### POST /admins

创建管理员账号。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | ✓ | 用户名（唯一） |
| password | string | ✓ | 明文密码（服务内部 bcrypt 加密存储） |
| real_name | string | - | 真实姓名 |
| phone | string | - | 手机号 |
| status | int | - | 1=启用 0=禁用，默认 1 |
| created_by | int | - | 创建者管理员 ID |

**请求示例**

```json
{
  "username": "operator01",
  "password": "Pwd@12345",
  "real_name": "运营员工",
  "phone": "13800000000"
}
```

**响应**：`201 Created`，`data` 为新建管理员对象（含 `id`、`public_id`）。

**错误**

| 状态码 | code | 说明 |
|--------|------|------|
| 409 | 40002 | 用户名已存在 |

---

### GET /admins/{admin_id}

获取单个管理员账号详情。

**路径参数**：`admin_id`（int）

**错误**

| 状态码 | code | 说明 |
|--------|------|------|
| 404 | 40001 | 管理员不存在 |

---

### PUT /admins/{admin_id}

更新管理员信息（仅传需要修改的字段）。

**请求体**（全部可选）

| 字段 | 类型 | 说明 |
|------|------|------|
| username | string | 新用户名 |
| real_name | string | 真实姓名 |
| phone | string | 手机号 |
| status | int | 1=启用 0=禁用 |

**错误**

| 状态码 | code | 说明 |
|--------|------|------|
| 404 | 40001 | 管理员不存在 |

---

### DELETE /admins/{admin_id}

删除管理员账号。

**错误**

| 状态码 | code | 说明 |
|--------|------|------|
| 404 | 40001 | 管理员不存在 |

**响应示例**

```json
{ "code": 0, "message": "success", "data": {"message": "deleted"}, "request_id": "..." }
```

---

### POST /admins/{admin_id}/roles

为管理员分配角色（全量覆盖）。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| role_ids | int[] | ✓ | 角色 ID 列表 |

**请求示例**

```json
{ "role_ids": [1, 2] }
```

**响应**：更新后的管理员对象。

**错误**

| 状态码 | code | 说明 |
|--------|------|------|
| 404 | 40001 | 管理员不存在 |

---

### POST /admins/{admin_id}/status

更新管理员启用/禁用状态。同时使 Redis 中该管理员的 token 版本号自增，令其所有旧 Token 立即失效。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | int | ✓ | 1=启用 0=禁用 |

**错误**

| 状态码 | code | 说明 |
|--------|------|------|
| 404 | 40001 | 管理员不存在 |

---

## 角色 Roles

### GET /roles

获取所有角色列表。

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": 1,
      "role_code": "super_admin",
      "role_name": "超级管理员",
      "is_system": 1,
      "status": 1
    }
  ],
  "request_id": "..."
}
```

---

### POST /roles

创建角色。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| role_code | string | ✓ | 角色唯一编码（如 `operator`） |
| role_name | string | ✓ | 角色显示名称 |
| is_system | int | - | 1=系统角色（不可删除），默认 0 |
| status | int | - | 1=启用 0=禁用，默认 1 |

**响应**：`201 Created`，`data` 为新建角色对象。

---

### PUT /roles/{role_id}

更新角色（仅传需要修改的字段）。

**请求体**（全部可选）

| 字段 | 类型 | 说明 |
|------|------|------|
| role_code | string | 角色编码 |
| role_name | string | 角色名称 |
| status | int | 1=启用 0=禁用 |

**错误**

| 状态码 | code | 说明 |
|--------|------|------|
| 404 | 40005 | 角色不存在 |

---

### DELETE /roles/{role_id}

删除角色。系统角色（`is_system=1`）不可删除。

**错误**

| 状态码 | code | 说明 |
|--------|------|------|
| 404 | 40005 | 角色不存在 |
| 409 | 40012 | 系统角色不可删除 |

---

### POST /roles/{role_id}/permissions

为角色分配权限（全量覆盖）。同时刷新 Redis 中绑定该角色的所有管理员的权限缓存。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| permission_ids | int[] | ✓ | 权限 ID 列表 |

**请求示例**

```json
{ "permission_ids": [1, 2, 5, 8] }
```

**错误**

| 状态码 | code | 说明 |
|--------|------|------|
| 404 | 40005 | 角色不存在 |

---

## 权限 Permissions

### GET /permissions

获取完整权限树（递归嵌套结构）。

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": 1,
      "parent_id": 0,
      "perm_code": "admin:manage",
      "perm_name": "管理员管理",
      "perm_type": 1,
      "path": "/admins",
      "method": null,
      "children": [
        {
          "id": 2,
          "parent_id": 1,
          "perm_code": "admin:create",
          "perm_name": "创建管理员",
          "perm_type": 2,
          "path": "/admins",
          "method": "POST",
          "children": []
        }
      ]
    }
  ],
  "request_id": "..."
}
```

---

### POST /permissions

创建权限节点。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| perm_code | string | ✓ | 权限唯一编码（如 `admin:create`） |
| perm_name | string | ✓ | 权限显示名称 |
| parent_id | int | - | 父权限 ID，顶层节点填 0（默认） |
| perm_type | int | - | 1=菜单 2=按钮 3=API |
| path | string | - | 关联路由路径 |
| method | string | - | HTTP 方法（GET/POST/PUT/DELETE/PATCH） |

**响应**：`201 Created`，`data` 为新建权限对象。

---

### PUT /permissions/{perm_id}

更新权限节点。

**请求体**（全部可选）

| 字段 | 类型 | 说明 |
|------|------|------|
| parent_id | int | 父权限 ID |
| perm_code | string | 权限编码 |
| perm_name | string | 权限名称 |
| perm_type | int | 1=菜单 2=按钮 3=API |
| path | string | 路由路径 |
| method | string | HTTP 方法 |

**错误**

| 状态码 | code | 说明 |
|--------|------|------|
| 404 | 40006 | 权限不存在 |

---

### DELETE /permissions/{perm_id}

删除权限节点。

**错误**

| 状态码 | code | 说明 |
|--------|------|------|
| 404 | 40006 | 权限不存在 |

---

## 操作日志 Audit Logs

### GET /audit-logs

分页查询操作审计日志，支持多条件过滤。

**Query 参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| admin_id | int | 按管理员 ID 过滤 |
| target_type | string | 按操作对象类型过滤（如 `merchant`、`order`、`rider`） |
| date_from | datetime | 开始时间（ISO 8601，如 `2026-03-01T00:00:00`） |
| date_to | datetime | 结束时间（ISO 8601） |
| page | int | 页码，默认 1 |
| page_size | int | 每页数量，默认 20，最大 100 |

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "admin_id": 1,
        "admin_name": "admin",
        "action": "UPDATE_STATUS",
        "target_type": "merchant",
        "target_id": 42,
        "request_body": "{\"status\": 0}",
        "ip": "127.0.0.1",
        "created_at": "2026-03-27T10:00:00"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  },
  "request_id": "..."
}
```

---

## 内部接口 Internal（服务间调用）

> 以下接口仅供内部服务调用，不对外暴露。Base URL 前缀为 `/internal`。

### GET /internal/admins/{admin_id}

供 auth-service 在管理员登录时查询权限列表，用于写入 JWT Token。

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "username": "admin",
    "permissions": ["admin:manage", "order:view"]
  },
  "request_id": "..."
}
```

**错误**

| 状态码 | code | 说明 |
|--------|------|------|
| 404 | 40001 | 管理员不存在 |

---

### POST /internal/audit-logs

供其他服务创建审计日志记录。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| admin_id | int | ✓ | 操作人管理员 ID |
| admin_name | string | - | 操作人用户名 |
| action | string | - | 操作动作（如 `UPDATE_STATUS`） |
| target_type | string | - | 操作对象类型（如 `merchant`） |
| target_id | int | - | 操作对象 ID |
| request_body | string | - | 请求体（JSON 字符串） |
| ip | string | - | 操作者 IP |

**响应**：`201 Created`，`data` 为创建的日志对象。

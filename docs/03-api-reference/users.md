# 用户管理 API

> 以下接口由 user-service（:8001）提供，前缀 `/api/users`，需要管理员权限。

## 获取管理员用户列表

```http
GET /api/users?page=1&size=20&keyword=alice
Authorization: Bearer <access_token>
```

**响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "username": "alice",
        "status": "active",
        "roles": ["admin"],
        "created_at": "2024-01-01T00:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "size": 20
  }
}
```

## 创建管理员用户

```http
POST /api/users
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "username": "bob",
  "password": "StrongPass123!",
  "role_ids": [1, 2]
}
```

## 获取用户详情

```http
GET /api/users/{id}
Authorization: Bearer <access_token>
```

## 更新用户信息

```http
PUT /api/users/{id}
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "username": "bob_new"
}
```

## 删除用户

```http
DELETE /api/users/{id}
Authorization: Bearer <access_token>
```

## 修改用户状态

```http
POST /api/users/{id}/status
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "status": "disabled"
}
```

状态变更后立即在 Redis 中更新，所有在线会话下次请求将收到 401。

## 分配角色

```http
POST /api/users/{id}/roles
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "role_ids": [1, 3]
}
```

此操作将**覆盖**用户当前的角色列表，并自动更新 Redis 权限版本号。

## 角色管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/roles` | 获取角色列表 |
| POST | `/api/roles` | 创建角色 |
| GET | `/api/roles/{id}` | 获取角色详情（含权限） |
| PUT | `/api/roles/{id}` | 更新角色 |
| DELETE | `/api/roles/{id}` | 删除角色 |
| POST | `/api/roles/{id}/permissions` | 覆盖分配权限 |

## 权限管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/permissions` | 获取权限列表 |
| POST | `/api/permissions` | 创建权限 |
| GET | `/api/permissions/{id}` | 获取权限详情 |
| PUT | `/api/permissions/{id}` | 更新权限 |
| DELETE | `/api/permissions/{id}` | 删除权限 |

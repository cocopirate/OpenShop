---
title: 认证 API
---

> 认证接口由 auth-service 提供，API Gateway 负责 JWT 校验。

## 登录

```http
POST /api/auth/admin/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your-password"
}
```

**响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 1800
  },
  "request_id": "uuid"
}
```

## 登出

```http
POST /api/auth/logout
Authorization: Bearer <access_token>
```

登出后，Redis 中的用户状态缓存将被清理，在线会话立即失效。

## JWT Payload 说明

```json
{
  "uid": 42,
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
| uid | int | 用户 ID |
| username | string | 用户名，日志追踪用 |
| roles | string[] | 角色列表，前端菜单渲染 |
| permissions | string[] | 权限码列表，Gateway 鉴权 |
| status | string | 账号状态快照，最终以 Redis 为准 |
| ver | int | 权限版本号 |
| exp | int | Unix 时间戳，默认 30 分钟后过期 |

## 鉴权流程

所有需鉴权的接口须在 Header 中携带 Bearer Token：

```
Authorization: Bearer <access_token>
```

API Gateway 校验流程：

1. 验证 JWT 签名（HS256）
2. 检查 Redis 中用户状态（`user_status:{uid}`）
3. 对比 JWT 中权限版本号与 Redis 版本（`user_perm_ver:{uid}`）
4. 检查当前路由是否在 `permissions` 列表中

详细设计见 [安全设计](../04-architecture/security.md)。

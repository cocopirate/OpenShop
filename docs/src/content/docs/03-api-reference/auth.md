---
title: 认证 API
---

> 认证接口由 **auth-service** 提供，经 API Gateway 转发，Gateway 同时负责 JWT 签名校验与权限版本核查。

所有响应均遵循统一格式：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... },
  "request_id": "uuid"
}
```

---

## 登录接口

### 用户端登录（手机号 + 密码）

```http
POST /auth/consumer/login
Content-Type: application/json

{
  "phone": "13800138000",
  "password": "your-password"
}
```

**响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "dGhpcyBpcyBhIHNlY3VyZSByZWZyZXNoIHRva2Vu...",
    "token_type": "bearer"
  },
  "request_id": "uuid"
}
```

### 用户端短信验证码登录 / 自动注册

```http
POST /auth/consumer/sms-login
Content-Type: application/json

{
  "phone": "13800138000",
  "code": "123456"
}
```

响应结构与手机号登录一致。手机号未注册时自动创建账户。

### 商户主账号登录

```http
POST /auth/merchant/login
Content-Type: application/json

{
  "phone": "13900139000",
  "password": "your-password"
}
```

**响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "dGhpcyBpcyBhIHNlY3VyZSByZWZyZXNoIHRva2Vu...",
    "merchant_id": "1001"
  },
  "request_id": "uuid"
}
```

### 商户子账号登录

```http
POST /auth/merchant-sub/login
Content-Type: application/json

{
  "username": "sub_user",
  "password": "your-password"
}
```

**响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "dGhpcyBpcyBhIHNlY3VyZSByZWZyZXNoIHRva2Vu...",
    "merchant_id": "1001",
    "permissions": ["order:list", "product:edit"]
  },
  "request_id": "uuid"
}
```

### 门店员工登录

```http
POST /auth/staff/login
Content-Type: application/json

{
  "phone": "13700137000",
  "password": "your-password"
}
```

**响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "dGhpcyBpcyBhIHNlY3VyZSByZWZyZXNoIHRva2Vu..."
  },
  "request_id": "uuid"
}
```

### 管理员登录

```http
POST /auth/admin/login
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
    "access_token": "eyJ...",
    "refresh_token": "dGhpcyBpcyBhIHNlY3VyZSByZWZyZXNoIHRva2Vu...",
    "token_type": "bearer"
  },
  "request_id": "uuid"
}
```

---

## 刷新 Token

```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "dGhpcyBpcyBhIHNlY3VyZSByZWZyZXNoIHRva2Vu..."
}
```

**响应：** 返回新的 `access_token` 与 `refresh_token`，结构与对应账号类型的登录响应一致。

旧 `refresh_token` 立即作废（旋转机制），请用新值替换本地存储。

| 账号类型 | 续期策略 |
|----------|----------|
| 管理员 / 商户 / 员工 | **固定窗口** — 30 天绝对有效期，每次刷新保留剩余时间，不延长 |
| 用户端（consumer） | **滑动窗口** — 每次刷新重置为 30 天，近 30 天内有访问则持续有效 |

**错误码：**

| code | 含义 |
|------|------|
| 40012 | refresh_token 无效或已过期 |

---

## 登出

```http
POST /auth/logout
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "refresh_token": "dGhpcyBpcyBhIHNlY3VyZSByZWZyZXNoIHRva2Vu..."
}
```

> `refresh_token` 为可选字段。传入时同步撤销该 refresh token；不传则仅使访问令牌失效。

登出后 Redis 中的权限版本号（`user_perm_ver:{biz_id}`）自增，所有当前签发的 access token 立即失效。

---

## Token 说明

| 类型 | 有效期 | 存储方式 |
|------|--------|----------|
| access_token | 2 小时 | JWT，HS256 签名，无需服务端存储 |
| refresh_token | 30 天 | 不透明随机字符串，存储在 Redis（`rt:{token}`） |

### JWT Payload 字段

```json
{
  "sub": "42",
  "uid": "42",
  "account_type": "admin",
  "permissions": ["user:list", "user:create"],
  "ver": 5,
  "exp": 1700008800
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| sub / uid | string | 业务用户 ID（biz_id） |
| account_type | string | `consumer` / `merchant` / `merchant_sub` / `merchant_staff` / `admin` |
| ver | int | 权限版本号，与 Redis `user_perm_ver:{biz_id}` 对比校验 |
| permissions | string[] | 仅 admin / merchant_sub 携带 |
| merchant_id | string | 仅 merchant / merchant_sub / merchant_staff 携带 |
| store_id | string | 仅 merchant_staff 携带 |
| job_type | string | 仅 merchant_staff 携带 |
| exp | int | Unix 时间戳，access token 2 小时后过期 |

---

## 鉴权流程

所有需鉴权的接口须在 Header 中携带：

```
Authorization: Bearer <access_token>
```

API Gateway 校验步骤：

1. 验证 JWT 签名（HS256）及过期时间
2. 从 Redis 读取 `user_perm_ver:{biz_id}`，与 JWT `ver` 字段对比；不一致则拒绝（表示已登出或权限变更）
3. 校验通过后将解析的 payload 以请求头（`X-User-*`）形式转发给下游服务

详细设计见 [安全设计](../04-architecture/security.md)。

---

## 用户端注册

```http
POST /auth/register/consumer
Content-Type: application/json

{
  "phone": "13800138000",
  "password": "your-password",
  "biz_id": 10001
}
```

**响应（HTTP 201）：**

```json
{
  "code": 0,
  "message": "success",
  "data": { "message": "consumer registered" },
  "request_id": "uuid"
}
```

| code | 含义 |
|------|------|
| 40002 | 手机号已注册 |

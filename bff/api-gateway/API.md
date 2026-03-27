# API Gateway — 接口文档

**网关地址**: `http://localhost:8080`  
**Content-Type**: `application/json`  
**认证方式**: `Authorization: Bearer <access_token>`

网关作为所有客户端流量的统一入口，负责 JWT 鉴权、路由转发、限流保护、请求日志记录，以及可配置的请求验签与 AES+RSA 加解密。所有下游服务均通过网关对外暴露。

---

## 目录

1. [认证说明](#认证说明)
2. [安全加密说明](#安全加密说明)
3. [路由规则](#路由规则)
4. [健康检查](#健康检查)
5. [认证 Auth（转发至 auth-service）](#认证-auth转发至-auth-service)
6. [管理员用户管理（转发至 admin-service）](#管理员用户管理转发至-admin-service)
7. [角色管理（转发至 admin-service）](#角色管理转发至-admin-service)
8. [权限管理（转发至 admin-service）](#权限管理转发至-admin-service)
9. [通用错误码](#通用错误码)

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
| POST | /api/auth/consumer/login |
| POST | /api/auth/merchant/login |
| POST | /api/auth/merchant-sub/login |
| POST | /api/auth/staff/login |
| POST | /api/auth/register/consumer |
| GET | /health |
| GET | /health/ready |
| GET | /metrics |

### 限流规则

- 每分钟最多 **60** 次请求
- 每小时最多 **1000** 次请求

---

## 安全加密说明

网关支持对指定接口进行**请求验签**、**AES+RSA 请求解密**和**AES 响应加密**，三项功能相互独立，通过路由 tag 精细配置。

### 配置方式

在路由定义上添加对应的 tag，中间件将自动对该接口启用相应安全功能：

| Tag | 功能 |
|-----|------|
| `require-sign` | 验证 `X-Timestamp` + `X-Sign` HMAC-SHA256 签名 |
| `require-encrypt-request` | 解密 AES+RSA 混合加密的请求体 |
| `require-encrypt-response` | 用 AES 会话密钥加密上游响应体（需同时添加 `require-encrypt-request`） |

**示例**

```python
@router.post("/api/v1/orders", tags=["require-sign", "require-encrypt-request",
                                     "require-encrypt-response"])
async def create_order(request: Request):
    ...
```

**密钥配置**（`.env` 文件）

| 环境变量 | 说明 | 示例 |
|---------|------|------|
| `CRYPTO_HMAC_SECRET` | HMAC-SHA256 签名密钥（验签用） | `change-this-secret` |
| `CRYPTO_RSA_PRIVATE_KEY` | 服务端 RSA 私钥（PEM 格式，用于解密客户端上传的 AES 会话密钥）| `-----BEGIN RSA PRIVATE KEY-----\n...` |

生成 RSA 密钥对示例：

```bash
# 生成 2048 位私钥
openssl genrsa -out private.pem 2048
# 导出公钥（客户端持有）
openssl rsa -in private.pem -pubout -out public.pem
```

---

### 请求验签（X-Sign / X-Timestamp）

当接口路由包含 `require-sign` tag 时，客户端必须在请求头中携带：

| 请求头 | 说明 |
|-------|------|
| `X-Timestamp` | Unix 时间戳（秒），服务端接受 ±5 分钟误差 |
| `X-Sign` | HMAC-SHA256 签名（十六进制小写） |

**签名字符串（String-to-sign）格式**

```
{timestamp}\n{METHOD}\n{path}\n{body_hex}
```

- `body_hex`：请求体原始字节的十六进制字符串（空 body 时为空字符串）
- 当接口同时开启了请求解密，签名是对**明文 body** 计算的

**Python 示例**

```python
import hashlib, hmac, time

def sign(body: bytes, method: str, path: str, secret: str) -> tuple[str, str]:
    ts = str(int(time.time()))
    string_to_sign = f"{ts}\n{method.upper()}\n{path}\n{body.hex()}"
    sig = hmac.new(secret.encode(), string_to_sign.encode(), hashlib.sha256).hexdigest()
    return ts, sig
```

**请求示例**

```http
POST /api/v1/orders HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
Content-Type: application/json
X-Timestamp: 1711411200
X-Sign: a3f9c2e1b4d7...

{"product_id": 42, "quantity": 1}
```

**验签失败响应（400）**

```json
{
  "code": 40013,
  "message": "Signature verification failed: Signature mismatch",
  "data": null,
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### AES+RSA 请求解密

当接口路由包含 `require-encrypt-request` tag 时，客户端应发送**混合加密**的请求体。

**加密流程（客户端）**

```
① 生成随机 AES-256 会话密钥（32 字节）和 IV（16 字节）
② 用 AES-256-CBC + PKCS7 Padding 加密原始请求 JSON → ciphertext
③ 用服务端 RSA 公钥（OAEP/SHA-256）加密 AES 会话密钥 → encrypted_key
④ 发送以下 JSON envelope 作为请求体
```

**请求体 Envelope 格式**

```json
{
  "encrypted_key": "<Base64(RSA-OAEP 加密后的 AES 密钥)>",
  "iv":            "<Base64(AES CBC IV, 16 字节)>",
  "data":          "<Base64(AES-256-CBC 加密后的原始请求体)>"
}
```

**Python 加密示例**

```python
import os, json, base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives import hashes, serialization

def encrypt_request(plaintext: bytes, public_key_pem: str) -> bytes:
    pub_key = serialization.load_pem_public_key(public_key_pem.encode())
    aes_key = os.urandom(32)
    iv = os.urandom(16)

    # AES-256-CBC with PKCS7 padding
    pad_len = 16 - (len(plaintext) % 16)
    padded = plaintext + bytes([pad_len] * pad_len)
    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
    ciphertext = cipher.encryptor().update(padded) + cipher.encryptor().finalize()

    enc_key = pub_key.encrypt(
        aes_key,
        asym_padding.OAEP(mgf=asym_padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
    )
    return json.dumps({
        "encrypted_key": base64.b64encode(enc_key).decode(),
        "iv": base64.b64encode(iv).decode(),
        "data": base64.b64encode(ciphertext).decode(),
    }).encode()
```

**解密失败响应（400）**

```json
{
  "code": 40014,
  "message": "Request decryption failed: Missing field in encrypted request envelope: 'data'",
  "data": null,
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### AES 响应加密

当接口路由同时包含 `require-encrypt-request` 和 `require-encrypt-response` tag 时，网关将用本次请求的 AES 会话密钥加密上游服务的响应体。

**响应体 Envelope 格式**

```json
{
  "iv":   "<Base64(AES CBC IV)>",
  "data": "<Base64(AES-256-CBC 加密后的原始响应体)>"
}
```

客户端用请求时生成的同一个 AES 会话密钥解密即可。

**Python 解密示例**

```python
import base64, json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

def decrypt_response(envelope_json: str, aes_key: bytes) -> bytes:
    env = json.loads(envelope_json)
    iv = base64.b64decode(env["iv"])
    ciphertext = base64.b64decode(env["data"])
    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
    padded = cipher.decryptor().update(ciphertext) + cipher.decryptor().finalize()
    pad_len = padded[-1]
    return padded[:-pad_len]
```

---

### 处理顺序

```
客户端请求
    ↓
① （若路径在解密列表）RSA 解密 AES 会话密钥 → AES 解密请求体 → 替换为明文
    ↓
② （若路径在验签列表）HMAC-SHA256 验证明文 body 签名
    ↓
③ JWT 鉴权 / 权限校验
    ↓
④ 转发至上游服务
    ↓
⑤ （若路径在响应加密列表）AES 加密响应体后返回客户端
```

---

## 路由规则

网关按最长前缀匹配将请求转发到对应下游服务：

| 路径前缀 | 上游服务 | 端口 |
|---------|---------|------|
| `/api/auth/**` | auth-service | 8000 |
| `/api/admins/**` | admin-service | 8012 |
| `/api/roles/**` | admin-service | 8012 |
| `/api/permissions/**` | admin-service | 8012 |
| `/api/v1/users/**` | consumer-service | 8001 |
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

## 认证 Auth（转发至 auth-service）

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
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOiI3YzE4MWQ3Yi00MjI0LTQxODktOTEzMi1mOWE4ZmM1OGEzNzMiLCJ1c2VybmFtZSI6ImFkbWluIiwicm9sZXMiOlsic3VwZXJhZG1pbiJdLCJwZXJtaXNzaW9ucyI6WyIqIl0sInN0YXR1cyI6ImFjdGl2ZSIsInZlciI6MCwiZXhwIjoxNzAwMDAxODAwfQ.example",
    "token_type": "bearer"
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**错误响应**

| 状态码 | 错误码 | 说明 |
|--------|--------|------|
| 401 | 40003 | 用户名或密码错误 |
| 403 | 40004 | 账号已被禁用 |

---

### POST /api/auth/logout

登出当前账号。调用后 Redis 中的权限版本号自增，该用户持有的所有旧 Token 立即失效。

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
  "code": 0,
  "message": "success",
  "data": {
    "message": "logged out"
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## 管理员用户管理（转发至 admin-service）

### GET /api/admins

获取管理员用户列表。

**所需权限**: `user:list`

**请求示例**

```http
GET /api/admins HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
```

```bash
curl http://localhost:8080/api/admins \
  -H "Authorization: Bearer <access_token>"
```

**响应示例（200 OK）**

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "public_id": "7c181d7b-4224-4189-9132-f9a8fc58a373",
      "username": "admin",
      "status": "active",
      "created_at": "2024-01-01T00:00:00"
    }
  ],
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### POST /api/admins

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
POST /api/admins HTTP/1.1
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
  http://localhost:8080/api/admins \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"username": "operator01", "password": "Operator@123", "status": "active"}'
```

**响应示例（201 Created）**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "public_id": "a1b2c3d4-0000-0000-0000-000000000001",
    "username": "operator01",
    "status": "active",
    "created_at": "2024-06-01T10:00:00"
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### GET /api/admins/{user_id}

获取指定管理员用户详情（`user_id` 为 UUID）。

**所需权限**: `user:list`

**请求示例**

```http
GET /api/admins/7c181d7b-4224-4189-9132-f9a8fc58a373 HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
```

```bash
curl http://localhost:8080/api/admins/7c181d7b-4224-4189-9132-f9a8fc58a373 \
  -H "Authorization: Bearer <access_token>"
```

**响应示例（200 OK）**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "public_id": "7c181d7b-4224-4189-9132-f9a8fc58a373",
    "username": "admin",
    "status": "active",
    "created_at": "2024-01-01T00:00:00"
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### PUT /api/admins/{user_id}

更新管理员用户信息。

**所需权限**: `user:update`

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | — | 新用户名 |
| status | string | — | `active` 或 `disabled` |

**请求示例**

```http
PUT /api/admins/7c181d7b-4224-4189-9132-f9a8fc58a373 HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "username": "admin_renamed"
}
```

```bash
curl -X PUT \
  http://localhost:8080/api/admins/7c181d7b-4224-4189-9132-f9a8fc58a373 \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin_renamed"}'
```

**响应示例（200 OK）**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "public_id": "7c181d7b-4224-4189-9132-f9a8fc58a373",
    "username": "admin_renamed",
    "status": "active",
    "created_at": "2024-01-01T00:00:00"
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### DELETE /api/admins/{user_id}

删除管理员用户。

**所需权限**: `user:delete`

**请求示例**

```http
DELETE /api/admins/a1b2c3d4-0000-0000-0000-000000000001 HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
```

```bash
curl -X DELETE \
  http://localhost:8080/api/admins/a1b2c3d4-0000-0000-0000-000000000001 \
  -H "Authorization: Bearer <access_token>"
```

**响应示例（200 OK）**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "message": "deleted"
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### POST /api/admins/{user_id}/status

启用或禁用管理员账号，立即生效。

**所需权限**: `user:update`

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | ✓ | `active` 或 `disabled` |

**请求示例（禁用账号）**

```http
POST /api/admins/a1b2c3d4-0000-0000-0000-000000000001/status HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "status": "disabled"
}
```

```bash
curl -X POST \
  http://localhost:8080/api/admins/a1b2c3d4-0000-0000-0000-000000000001/status \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"status": "disabled"}'
```

**响应示例（200 OK）**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "public_id": "a1b2c3d4-0000-0000-0000-000000000001",
    "username": "operator01",
    "status": "disabled",
    "created_at": "2024-06-01T10:00:00"
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### POST /api/admins/{user_id}/roles

为管理员用户批量分配角色（全量覆盖）。

**所需权限**: `user:update`

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| role_ids | array[int] | ✓ | 角色 ID 列表 |

**请求示例**

```http
POST /api/admins/a1b2c3d4-0000-0000-0000-000000000001/roles HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "role_ids": [1, 2]
}
```

```bash
curl -X POST \
  http://localhost:8080/api/admins/a1b2c3d4-0000-0000-0000-000000000001/roles \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"role_ids": [1, 2]}'
```

**响应示例（200 OK）**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "public_id": "a1b2c3d4-0000-0000-0000-000000000001",
    "username": "operator01",
    "status": "active",
    "created_at": "2024-06-01T10:00:00"
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## 角色管理（转发至 admin-service）

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
{
  "code": 0,
  "message": "success",
  "data": [
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
  ],
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
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
  "code": 0,
  "message": "success",
  "data": {
    "id": 2,
    "name": "operator",
    "desc": "运营人员",
    "created_at": "2024-06-01T10:00:00"
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
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
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "name": "superadmin",
    "desc": "超级管理员，拥有全部权限",
    "created_at": "2024-01-01T00:00:00"
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
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
  "code": 0,
  "message": "success",
  "data": {
    "id": 2,
    "name": "operator",
    "desc": "运营人员（已更新描述）",
    "created_at": "2024-01-02T00:00:00"
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
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
  "code": 0,
  "message": "success",
  "data": {
    "message": "deleted"
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
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
  "code": 0,
  "message": "success",
  "data": {
    "id": 2,
    "name": "operator",
    "desc": "运营人员",
    "created_at": "2024-01-02T00:00:00"
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## 权限管理（转发至 admin-service）

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
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": 1,
      "code": "user:list",
      "name": "查看管理员用户",
      "type": "api",
      "method": "GET",
      "path": "/api/admins",
      "parent_id": null,
      "created_at": "2024-01-01T00:00:00"
    }
  ],
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
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
  "code": 0,
  "message": "success",
  "data": {
    "id": 10,
    "code": "report:view",
    "name": "查看报表",
    "type": "api",
    "method": "GET",
    "path": "/api/v1/reports",
    "parent_id": null,
    "created_at": "2024-06-01T10:00:00"
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
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
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "code": "user:list",
    "name": "查看管理员用户",
    "type": "api",
    "method": "GET",
    "path": "/api/admins",
    "parent_id": null,
    "created_at": "2024-01-01T00:00:00"
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
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
  "code": 0,
  "message": "success",
  "data": {
    "id": 10,
    "code": "report:view",
    "name": "查看所有报表",
    "type": "api",
    "method": "GET",
    "path": "/api/v1/reports",
    "parent_id": null,
    "created_at": "2024-06-01T10:00:00"
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
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
  "code": 0,
  "message": "success",
  "data": {
    "message": "deleted"
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## 通用错误码

| 状态码 | 错误码 | 说明 |
|--------|--------|------|
| 400 | 40011 | 请求参数校验失败 |
| 400 | 40012 | 缺少签名请求头（X-Timestamp 或 X-Sign） |
| 400 | 40013 | 请求签名验证失败 |
| 400 | 40014 | 请求体解密失败 |
| 401 | 40007 | 未认证、Token 无效/过期/被撤销，或账号已禁用 |
| 403 | 40010 | 缺少所需权限 |
| 404 | 50003 | 路径无匹配的上游服务，或资源不存在 |
| 422 | 40011 | 请求体格式错误 |
| 500 | 50004 | 网关加解密配置错误 |
| 503 | 50001 | 上游服务不可用（连接失败） |
| 504 | 50002 | 上游服务超时（默认 30s） |

**401 响应示例（Token 被撤销）**

```json
{
  "code": 40007,
  "message": "Token invalidated, please login again",
  "data": null,
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**401 响应示例（用户已禁用）**

```json
{
  "code": 40007,
  "message": "User is disabled",
  "data": null,
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**403 响应示例**

```json
{
  "code": 40010,
  "message": "Missing permission: user:create",
  "data": null,
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**503 响应示例**

```json
{
  "code": 50001,
  "message": "Upstream service unavailable",
  "data": null,
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

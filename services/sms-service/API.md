# SMS Service — 接口文档

**Base URL（直连）**: `http://localhost:8010`  
**Base URL（经网关）**: `http://localhost:8080`  
**Content-Type**: `application/json`

---

## 目录

1. [健康检查](#健康检查)
2. [短信发送 SMS Send](#短信发送-sms-send)
3. [发送记录查询 SMS Records](#发送记录查询-sms-records)
4. [验证码验证 SMS Verify](#验证码验证-sms-verify)
5. [管理后台 Admin](#管理后台-admin)
   - [发送记录管理](#发送记录管理)
   - [短信模板管理](#短信模板管理)
   - [短信配置管理](#短信配置管理)
6. [状态枚举](#状态枚举)
7. [通用错误码](#通用错误码)

---

## 健康检查

### GET /health

服务存活检查，同时验证数据库与 Redis 连接。

**无需认证**

**请求示例**

```http
GET /health HTTP/1.1
Host: localhost:8010
```

```bash
curl http://localhost:8010/health
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
Host: localhost:8010
```

```bash
curl http://localhost:8010/health/ready
```

**响应示例（200 OK）**

```json
{
  "status": "ready"
}
```

---

## 短信发送 SMS Send

### POST /api/v1/sms/send

发送短信，支持模板变量替换。可提供 `request_id` 作为幂等键，防止重复发送。

**无需认证**

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| phone | string | ✓ | 手机号（E.164 格式或本地格式） |
| template_id | string | ✓ | 短信模板标识符 |
| params | object | — | 模板变量，默认为空对象 |
| request_id | string | — | 客户端幂等键，最长 64 个字符 |

**请求示例**

```http
POST /api/v1/sms/send HTTP/1.1
Host: localhost:8010
Content-Type: application/json

{
  "phone": "13800138000",
  "template_id": "SMS_ORDER_SHIPPED",
  "params": {
    "orderId": "ORD-001",
    "company": "顺丰速运"
  },
  "request_id": "req-abc-001"
}
```

```bash
curl -X POST http://localhost:8010/api/v1/sms/send \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800138000","template_id":"SMS_ORDER_SHIPPED","params":{"orderId":"ORD-001","company":"顺丰速运"},"request_id":"req-abc-001"}'
```

**响应示例（201 Created）**

```json
{
  "message_id": "aliyun-msg-20240601-001",
  "request_id": "req-abc-001",
  "status": "SENT",
  "provider": "aliyun",
  "phone_masked": "138****8000"
}
```

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 422 | 请求体格式错误 |
| 429 | 触发限频（手机号或 IP 维度） |

**429 响应示例（手机号限频）**

```json
{
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "Phone rate limit exceeded. Retry after 45s",
  "retry_after": 45,
  "limit": 5,
  "window": 60
}
```

---

### POST /api/v1/sms/send-code

发送验证码短信，验证码由服务端生成并存入 Redis，TTL 由 `SMS_CODE_TTL` 配置（默认 300 秒）。

**无需认证**

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| phone | string | ✓ | 手机号 |
| template_id | string | ✓ | 短信模板标识符 |

**请求示例**

```http
POST /api/v1/sms/send-code?phone=13800138000&template_id=SMS_VERIFY_CODE HTTP/1.1
Host: localhost:8010
```

```bash
curl -X POST "http://localhost:8010/api/v1/sms/send-code?phone=13800138000&template_id=SMS_VERIFY_CODE"
```

**响应示例（201 Created）**

```json
{
  "message": "verification code sent"
}
```

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 429 | 触发限频 |

---

## 发送记录查询 SMS Records

### GET /api/v1/sms/records

查询短信发送记录，支持手机号、时间范围、状态过滤与分页。手机号以脱敏形式返回。

**无需认证**

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| phone | string | — | 按手机号过滤 |
| start_time | string | — | 开始时间（ISO 8601） |
| end_time | string | — | 结束时间（ISO 8601） |
| status | string | — | 状态过滤（`PENDING`/`SENT`/`DELIVERED`/`FAILED`） |
| page | int | — | 页码，默认 1 |
| size | int | — | 每页条数，默认 20，最大 100 |

**请求示例**

```http
GET /api/v1/sms/records?phone=13800138000&status=SENT&page=1&size=20 HTTP/1.1
Host: localhost:8010
```

```bash
curl "http://localhost:8010/api/v1/sms/records?phone=13800138000&status=SENT&page=1&size=20"
```

**响应示例（200 OK）**

```json
{
  "total": 1,
  "page": 1,
  "size": 20,
  "items": [
    {
      "id": 1,
      "request_id": "req-abc-001",
      "phone_masked": "138****8000",
      "template_id": "SMS_ORDER_SHIPPED",
      "provider": "aliyun",
      "provider_message_id": "aliyun-msg-20240601-001",
      "status": "SENT",
      "error_code": null,
      "error_message": null,
      "created_at": "2024-06-01T10:00:00",
      "updated_at": "2024-06-01T10:00:01"
    }
  ]
}
```

---

## 验证码验证 SMS Verify

### POST /api/v1/sms/verify

验证用户输入的短信验证码是否正确。

**无需认证**

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| phone | string | ✓ | 手机号 |
| code | string | ✓ | 用户输入的验证码 |

**请求示例**

```http
POST /api/v1/sms/verify HTTP/1.1
Host: localhost:8010
Content-Type: application/json

{
  "phone": "13800138000",
  "code": "123456"
}
```

```bash
curl -X POST http://localhost:8010/api/v1/sms/verify \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800138000","code":"123456"}'
```

**响应示例（200 OK — 验证通过）**

```json
{
  "phone": "13800138000",
  "valid": true
}
```

**响应示例（200 OK — 验证失败）**

```json
{
  "phone": "13800138000",
  "valid": false
}
```

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 422 | 验证码无效或已过期 |

---

## 管理后台 Admin

> 以下接口前缀为 `/api/v1/admin`，仅限管理员调用。鉴权由 API Gateway 的 RBAC 层负责，请求到达 sms-service 前须通过角色验证。

---

### 发送记录管理

#### GET /api/v1/admin/sms/records

查询短信发送记录（管理视图，手机号不脱敏）。过滤与分页参数同公开接口。

**请求示例**

```http
GET /api/v1/admin/sms/records?phone=13800138000&status=FAILED&page=1&size=20 HTTP/1.1
Host: localhost:8010
Authorization: Bearer <access_token>
```

```bash
curl "http://localhost:8010/api/v1/admin/sms/records?phone=13800138000&status=FAILED&page=1&size=20" \
  -H "Authorization: Bearer <access_token>"
```

**响应示例（200 OK）**

```json
{
  "total": 1,
  "page": 1,
  "size": 20,
  "items": [
    {
      "id": 2,
      "request_id": null,
      "phone_masked": "13800138000",
      "template_id": "SMS_ORDER_SHIPPED",
      "provider": "aliyun",
      "provider_message_id": null,
      "status": "FAILED",
      "error_code": "PROVIDER_ERROR",
      "error_message": "Invalid template",
      "created_at": "2024-06-01T11:00:00",
      "updated_at": "2024-06-01T11:00:01"
    }
  ]
}
```

---

#### DELETE /api/v1/admin/sms/records/{record_id}

删除指定短信发送记录。

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| record_id | int | 记录 ID |

**请求示例**

```http
DELETE /api/v1/admin/sms/records/2 HTTP/1.1
Host: localhost:8010
Authorization: Bearer <access_token>
```

```bash
curl -X DELETE http://localhost:8010/api/v1/admin/sms/records/2 \
  -H "Authorization: Bearer <access_token>"
```

**响应示例（204 No Content）**

无响应体。

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 404 | 记录不存在 |

---

### 短信模板管理

#### GET /api/v1/admin/sms/templates

查询短信模板列表，支持供应商和状态过滤。

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| provider | string | — | 按供应商过滤（`aliyun`/`tencent`/`chuanglan`） |
| is_active | bool | — | 按启用状态过滤 |
| page | int | — | 页码，默认 1 |
| size | int | — | 每页条数，默认 20，最大 100 |

**请求示例**

```http
GET /api/v1/admin/sms/templates?provider=aliyun&is_active=true&page=1&size=20 HTTP/1.1
Host: localhost:8010
Authorization: Bearer <access_token>
```

```bash
curl "http://localhost:8010/api/v1/admin/sms/templates?provider=aliyun&is_active=true&page=1&size=20" \
  -H "Authorization: Bearer <access_token>"
```

**响应示例（200 OK）**

```json
{
  "total": 2,
  "page": 1,
  "size": 20,
  "items": [
    {
      "id": 1,
      "provider_template_id": "SMS_123456789",
      "name": "订单发货通知",
      "content": "您的订单 ${orderId} 已由 ${company} 揽收，请注意查收。",
      "provider": "aliyun",
      "is_active": true,
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    },
    {
      "id": 2,
      "provider_template_id": "SMS_987654321",
      "name": "验证码",
      "content": "您的验证码为 ${code}，${ttl} 分钟内有效，请勿泄露。",
      "provider": "aliyun",
      "is_active": true,
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    }
  ]
}
```

---

#### POST /api/v1/admin/sms/templates

创建短信模板。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| provider_template_id | string | ✓ | 供应商模板 ID，最长 64 字符 |
| name | string | ✓ | 本地模板名称，最长 128 字符 |
| content | string | ✓ | 模板内容，可包含变量占位符 |
| provider | string | ✓ | 供应商名称（`aliyun`/`tencent`/`chuanglan`），最长 32 字符 |
| is_active | bool | — | 是否启用，默认 `true` |

**请求示例**

```http
POST /api/v1/admin/sms/templates HTTP/1.1
Host: localhost:8010
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "provider_template_id": "SMS_123456789",
  "name": "订单发货通知",
  "content": "您的订单 ${orderId} 已由 ${company} 揽收，请注意查收。",
  "provider": "aliyun",
  "is_active": true
}
```

```bash
curl -X POST http://localhost:8010/api/v1/admin/sms/templates \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"provider_template_id":"SMS_123456789","name":"订单发货通知","content":"您的订单 ${orderId} 已由 ${company} 揽收，请注意查收。","provider":"aliyun","is_active":true}'
```

**响应示例（201 Created）**

```json
{
  "id": 1,
  "provider_template_id": "SMS_123456789",
  "name": "订单发货通知",
  "content": "您的订单 ${orderId} 已由 ${company} 揽收，请注意查收。",
  "provider": "aliyun",
  "is_active": true,
  "created_at": "2024-06-01T10:00:00",
  "updated_at": "2024-06-01T10:00:00"
}
```

---

#### GET /api/v1/admin/sms/templates/{template_id}

获取指定短信模板详情。

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| template_id | int | 模板 ID |

**请求示例**

```http
GET /api/v1/admin/sms/templates/1 HTTP/1.1
Host: localhost:8010
Authorization: Bearer <access_token>
```

```bash
curl http://localhost:8010/api/v1/admin/sms/templates/1 \
  -H "Authorization: Bearer <access_token>"
```

**响应示例（200 OK）**

```json
{
  "id": 1,
  "provider_template_id": "SMS_123456789",
  "name": "订单发货通知",
  "content": "您的订单 ${orderId} 已由 ${company} 揽收，请注意查收。",
  "provider": "aliyun",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 404 | 模板不存在 |

---

#### PUT /api/v1/admin/sms/templates/{template_id}

更新指定短信模板（字段均为可选，仅传需修改的字段）。

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| template_id | int | 模板 ID |

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | — | 新模板名称，最长 128 字符 |
| content | string | — | 新模板内容 |
| provider | string | — | 新供应商，最长 32 字符 |
| is_active | bool | — | 启用/禁用 |

**请求示例**

```http
PUT /api/v1/admin/sms/templates/1 HTTP/1.1
Host: localhost:8010
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "is_active": false
}
```

```bash
curl -X PUT http://localhost:8010/api/v1/admin/sms/templates/1 \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"is_active":false}'
```

**响应示例（200 OK）**

```json
{
  "id": 1,
  "provider_template_id": "SMS_123456789",
  "name": "订单发货通知",
  "content": "您的订单 ${orderId} 已由 ${company} 揽收，请注意查收。",
  "provider": "aliyun",
  "is_active": false,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-06-01T10:00:00"
}
```

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 404 | 模板不存在 |

---

#### DELETE /api/v1/admin/sms/templates/{template_id}

删除指定短信模板。

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| template_id | int | 模板 ID |

**请求示例**

```http
DELETE /api/v1/admin/sms/templates/1 HTTP/1.1
Host: localhost:8010
Authorization: Bearer <access_token>
```

```bash
curl -X DELETE http://localhost:8010/api/v1/admin/sms/templates/1 \
  -H "Authorization: Bearer <access_token>"
```

**响应示例（204 No Content）**

无响应体。

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 404 | 模板不存在 |

---

### 短信配置管理

#### GET /api/v1/admin/sms/config

查询当前短信服务运行时配置。敏感密钥（AccessKey 等）不在返回字段内。

**请求示例**

```http
GET /api/v1/admin/sms/config HTTP/1.1
Host: localhost:8010
Authorization: Bearer <access_token>
```

```bash
curl http://localhost:8010/api/v1/admin/sms/config \
  -H "Authorization: Bearer <access_token>"
```

**响应示例（200 OK）**

```json
{
  "sms_provider": "aliyun",
  "sms_provider_fallback": "tencent",
  "sms_provider_failure_threshold": 5,
  "sms_provider_recovery_timeout": 60,
  "sms_code_ttl": 300,
  "sms_rate_limit_phone_per_minute": 1,
  "sms_rate_limit_phone_per_day": 10,
  "sms_rate_limit_ip_per_minute": 5,
  "sms_rate_limit_ip_per_day": 100,
  "sms_records_retention_days": 90
}
```

---

#### PUT /api/v1/admin/sms/config

动态更新短信服务配置，运行时立即生效。注意：重启服务后将恢复为环境变量中的值，如需永久生效请同步更新环境变量。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| sms_provider | string | — | 主供应商（`aliyun`/`tencent`/`chuanglan`） |
| sms_provider_fallback | string | — | 备用供应商，空字符串表示不启用 |
| sms_provider_failure_threshold | int | — | 熔断器失败阈值，最小为 1 |
| sms_provider_recovery_timeout | int | — | 熔断器恢复超时（秒），最小为 1 |
| sms_code_ttl | int | — | 验证码有效期（秒），最小为 60 |
| sms_rate_limit_phone_per_minute | int | — | 每手机号每分钟发送上限，最小为 1 |
| sms_rate_limit_phone_per_day | int | — | 每手机号每日发送上限，最小为 1 |
| sms_rate_limit_ip_per_minute | int | — | 每 IP 每分钟发送上限，最小为 1 |
| sms_rate_limit_ip_per_day | int | — | 每 IP 每日发送上限，最小为 1 |
| sms_records_retention_days | int | — | 发送记录保留天数，0 表示永久保留 |

**请求示例**

```http
PUT /api/v1/admin/sms/config HTTP/1.1
Host: localhost:8010
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "sms_provider": "tencent",
  "sms_code_ttl": 600
}
```

```bash
curl -X PUT http://localhost:8010/api/v1/admin/sms/config \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"sms_provider":"tencent","sms_code_ttl":600}'
```

**响应示例（200 OK）**

```json
{
  "sms_provider": "tencent",
  "sms_provider_fallback": "tencent",
  "sms_provider_failure_threshold": 5,
  "sms_provider_recovery_timeout": 60,
  "sms_code_ttl": 600,
  "sms_rate_limit_phone_per_minute": 1,
  "sms_rate_limit_phone_per_day": 10,
  "sms_rate_limit_ip_per_minute": 5,
  "sms_rate_limit_ip_per_day": 100,
  "sms_records_retention_days": 90
}
```

---

## 状态枚举

### SmsStatus

| 值 | 说明 |
|----|------|
| `PENDING` | 已提交，等待发送 |
| `SENT` | 已发送至供应商 |
| `DELIVERED` | 已成功送达手机 |
| `FAILED` | 发送失败 |

---

## 通用错误码

| 状态码 | 说明 |
|--------|------|
| 400 | 请求参数校验失败 |
| 404 | 资源不存在 |
| 422 | 请求体格式错误（FastAPI Unprocessable Entity） |
| 429 | 触发发送频率限制 |
| 500 | 服务器内部错误 |

**404 响应示例**

```json
{
  "detail": "SMS template 999 not found"
}
```

**429 响应示例（IP 限频）**

```json
{
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "IP rate limit exceeded. Retry after 55s",
  "retry_after": 55,
  "limit": 5,
  "window": 60
}
```

# SMS Service — 接口文档

**Base URL（直连）**: `http://localhost:8010`  
**Base URL（经网关）**: `http://localhost:8080`（网关路由前缀：`/api/sms` → sms-service）  
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

服务存活检查，同时验证数据库与 Redis 连通性。全部依赖正常时 `status` 为 `"ok"`，任意依赖异常时为 `"degraded"`。

**无需认证**

**请求示例**

```http
GET /health HTTP/1.1
Host: localhost:8010
```

```bash
curl http://localhost:8010/health
```

**响应示例（200 OK — 全部正常）**

```json
{
  "status": "ok",
  "service": "sms-service",
  "checks": {
    "database": "ok",
    "redis": "ok"
  }
}
```

**响应示例（200 OK — 部分异常）**

```json
{
  "status": "degraded",
  "service": "sms-service",
  "checks": {
    "database": "error",
    "redis": "ok"
  },
  "errors": {
    "database": "connection refused"
  }
}
```

---

## 短信发送 SMS Send

### POST /api/sms/send

发送短信，支持模板变量替换。可提供 `request_id` 作为幂等键防止重复发送。请求到达前会依次检查手机号维度与 IP 维度的发送频率限制。

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
POST /api/sms/send HTTP/1.1
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
curl -X POST http://localhost:8010/api/sms/send \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800138000","template_id":"SMS_ORDER_SHIPPED","params":{"orderId":"ORD-001","company":"顺丰速运"},"request_id":"req-abc-001"}'
```

**响应示例（201 Created）**

```json
{
  "message_id": "1",
  "request_id": "req-abc-001",
  "status": "SENT",
  "provider": "chuanglan",
  "phone_masked": "138****8000"
}
```

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 422 | 请求体格式校验失败 |
| 429 | 触发限频（手机号或 IP 维度） |

**429 响应示例（手机号限频）**

```json
{
  "code": 40501,
  "message": "Phone rate limit exceeded. Retry after 45s",
  "data": null,
  "request_id": "a4273592-26e4-4310-a68f-81adebeb9dbc"
}
```

响应 Header 中同时包含 `Retry-After: 45`。

**429 响应示例（IP 限频）**

```json
{
  "code": 40501,
  "message": "IP rate limit exceeded. Retry after 55s",
  "data": null,
  "request_id": "b1234567-89ab-cdef-0123-456789abcdef"
}
```

响应 Header 中同时包含 `Retry-After: 55`。

---

### POST /api/sms/send-code

发送验证码短信。验证码由服务端生成并写入 Redis，TTL 由 `SMS_CODE_TTL` 配置（默认 300 秒）。同样受手机号与 IP 维度限频控制。

**无需认证**

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| phone | string | ✓ | 手机号 |
| template_id | string | ✓ | 短信模板标识符 |

**请求示例**

```http
POST /api/sms/send-code?phone=13800138000&template_id=SMS_VERIFY_CODE HTTP/1.1
Host: localhost:8010
```

```bash
curl -X POST "http://localhost:8010/api/sms/send-code?phone=13800138000&template_id=SMS_VERIFY_CODE"
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

### GET /api/sms/records

查询短信发送记录，支持手机号、时间范围、状态过滤与分页。`phone_masked` 字段以脱敏形式返回手机号。结果按创建时间倒序排列，每页最多 100 条。

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
GET /api/sms/records?phone=13800138000&status=SENT&page=1&size=20 HTTP/1.1
Host: localhost:8010
```

```bash
curl "http://localhost:8010/api/sms/records?phone=13800138000&status=SENT&page=1&size=20"
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
      "provider": "chuanglan",
      "provider_message_id": "msg-20240601-001",
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

### POST /api/sms/verify

验证用户输入的短信验证码。验证通过返回 200 并附 `valid: true`；验证失败（验证码错误或已过期）返回 422。

**无需认证**

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| phone | string | ✓ | 手机号 |
| code | string | ✓ | 用户输入的验证码 |

**请求示例**

```http
POST /api/sms/verify HTTP/1.1
Host: localhost:8010
Content-Type: application/json

{
  "phone": "13800138000",
  "code": "123456"
}
```

```bash
curl -X POST http://localhost:8010/api/sms/verify \
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

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 422 | 验证码错误或已过期 |

**422 响应示例**

```json
{
  "detail": "invalid or expired verification code"
}
```

---

## 管理后台 Admin

> 以下接口仅限管理员调用，须携带有效 JWT。鉴权由 API Gateway 统一处理。
>
> | 访问方式 | Base URL | 路由前缀 |
> |----------|----------|----------|
> | 直连 sms-service | `http://localhost:8010` | `/api/sms/admin` |
> | 经网关（推荐） | `http://localhost:8080` | `/api/sms/admin` |

---

### 发送记录管理

#### GET /api/sms/records

查询短信发送记录（管理视图）。过滤与分页参数同公开接口，每页最多 100 条。

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| phone | string | — | 按手机号过滤 |
| start_time | string | — | 开始时间（ISO 8601） |
| end_time | string | — | 结束时间（ISO 8601） |
| status | string | — | 状态过滤（`PENDING`/`SENT`/`DELIVERED`/`FAILED`） |
| page | int | — | 页码，默认 1 |
| size | int | — | 每页条数，默认 20，最大 100 |

**请求示例（经网关）**

```http
GET /api/sms/admin/records?phone=13800138000&status=FAILED&page=1&size=20 HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
```

```bash
curl "http://localhost:8080/api/sms/admin/records?phone=13800138000&status=FAILED&page=1&size=20" \
  -H "Authorization: Bearer <access_token>"
```

**请求示例（直连）**

```http
GET /api/sms/admin/records?phone=13800138000&status=FAILED&page=1&size=20 HTTP/1.1
Host: localhost:8010
Authorization: Bearer <access_token>
```

```bash
curl "http://localhost:8010/api/sms/admin/records?phone=13800138000&status=FAILED&page=1&size=20" \
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
      "phone_masked": "138****8000",
      "template_id": "SMS_ORDER_SHIPPED",
      "provider": "chuanglan",
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

#### DELETE /api/sms/records/{record_id}

删除指定短信发送记录。

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| record_id | int | 记录 ID |

**请求示例（经网关）**

```http
DELETE /api/sms/admin/records/2 HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
```

```bash
curl -X DELETE http://localhost:8080/api/sms/admin/records/2 \
  -H "Authorization: Bearer <access_token>"
```

**请求示例（直连）**

```http
DELETE /api/sms/admin/records/2 HTTP/1.1
Host: localhost:8010
Authorization: Bearer <access_token>
```

```bash
curl -X DELETE http://localhost:8010/api/sms/admin/records/2 \
  -H "Authorization: Bearer <access_token>"
```

**响应示例（204 No Content）**

无响应体。

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 404 | 记录不存在 |

**404 响应示例**

```json
{
  "detail": "SMS record 2 not found"
}
```

---

### 短信模板管理

#### GET /api/sms/admin/templates

查询短信模板列表，支持供应商和启用状态过滤，分页返回。

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| provider | string | — | 按供应商过滤（`aliyun`/`tencent`/`chuanglan`） |
| is_active | bool | — | 按启用状态过滤 |
| page | int | — | 页码，默认 1 |
| size | int | — | 每页条数，默认 20，最大 100 |

**请求示例（经网关）**

```http
GET /api/sms/admin/templates?provider=chuanglan&is_active=true&page=1&size=20 HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
```

```bash
curl "http://localhost:8080/api/sms/admin/templates?provider=chuanglan&is_active=true&page=1&size=20" \
  -H "Authorization: Bearer <access_token>"
```

**请求示例（直连）**

```http
GET /api/sms/admin/templates?provider=chuanglan&is_active=true&page=1&size=20 HTTP/1.1
Host: localhost:8010
Authorization: Bearer <access_token>
```

```bash
curl "http://localhost:8010/api/sms/admin/templates?provider=chuanglan&is_active=true&page=1&size=20" \
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
      "id": 1,
      "provider_template_id": "TPL_123456",
      "name": "订单发货通知",
      "content": "您的订单 ${orderId} 已由 ${company} 揽收，请注意查收。",
      "provider": "chuanglan",
      "is_active": true,
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    }
  ]
}
```

---

#### POST /api/sms/admin/templates

创建短信模板。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| provider_template_id | string | ✓ | 供应商模板 ID，最长 64 字符 |
| name | string | ✓ | 本地模板名称，最长 128 字符 |
| content | string | ✓ | 模板内容，可包含变量占位符 |
| provider | string | ✓ | 供应商名称（`aliyun`/`tencent`/`chuanglan`），最长 32 字符 |
| is_active | bool | — | 是否启用，默认 `true` |

**请求示例（经网关）**

```http
POST /api/sms/admin/templates HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "provider_template_id": "TPL_123456",
  "name": "订单发货通知",
  "content": "您的订单 ${orderId} 已由 ${company} 揽收，请注意查收。",
  "provider": "chuanglan",
  "is_active": true
}
```

```bash
curl -X POST http://localhost:8080/api/sms/admin/templates \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"provider_template_id":"TPL_123456","name":"订单发货通知","content":"您的订单 ${orderId} 已由 ${company} 揽收，请注意查收。","provider":"chuanglan","is_active":true}'
```

**请求示例（直连）**

```http
POST /api/sms/admin/templates HTTP/1.1
Host: localhost:8010
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "provider_template_id": "TPL_123456",
  "name": "订单发货通知",
  "content": "您的订单 ${orderId} 已由 ${company} 揽收，请注意查收。",
  "provider": "chuanglan",
  "is_active": true
}
```

```bash
curl -X POST http://localhost:8010/api/sms/admin/templates \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"provider_template_id":"TPL_123456","name":"订单发货通知","content":"您的订单 ${orderId} 已由 ${company} 揽收，请注意查收。","provider":"chuanglan","is_active":true}'
```

**响应示例（201 Created）**

```json
{
  "id": 1,
  "provider_template_id": "TPL_123456",
  "name": "订单发货通知",
  "content": "您的订单 ${orderId} 已由 ${company} 揽收，请注意查收。",
  "provider": "chuanglan",
  "is_active": true,
  "created_at": "2024-06-01T10:00:00",
  "updated_at": "2024-06-01T10:00:00"
}
```

---

#### GET /api/sms/admin/templates/{template_id}

获取指定短信模板详情。

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| template_id | int | 模板 ID |

**请求示例（经网关）**

```http
GET /api/sms/admin/templates/1 HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
```

```bash
curl http://localhost:8080/api/sms/admin/templates/1 \
  -H "Authorization: Bearer <access_token>"
```

**请求示例（直连）**

```http
GET /api/sms/admin/templates/1 HTTP/1.1
Host: localhost:8010
Authorization: Bearer <access_token>
```

```bash
curl http://localhost:8010/api/sms/admin/templates/1 \
  -H "Authorization: Bearer <access_token>"
```

**响应示例（200 OK）**

```json
{
  "id": 1,
  "provider_template_id": "TPL_123456",
  "name": "订单发货通知",
  "content": "您的订单 ${orderId} 已由 ${company} 揽收，请注意查收。",
  "provider": "chuanglan",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 404 | 模板不存在 |

**404 响应示例**

```json
{
  "detail": "SMS template 1 not found"
}
```

---

#### PUT /api/sms/admin/templates/{template_id}

局部更新短信模板（仅传需修改的字段）。

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

**请求示例（经网关）**

```http
PUT /api/sms/admin/templates/1 HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "is_active": false
}
```

```bash
curl -X PUT http://localhost:8080/api/sms/admin/templates/1 \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"is_active":false}'
```

**请求示例（直连）**

```http
PUT /api/sms/admin/templates/1 HTTP/1.1
Host: localhost:8010
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "is_active": false
}
```

```bash
curl -X PUT http://localhost:8010/api/sms/admin/templates/1 \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"is_active":false}'
```

**响应示例（200 OK）**

```json
{
  "id": 1,
  "provider_template_id": "TPL_123456",
  "name": "订单发货通知",
  "content": "您的订单 ${orderId} 已由 ${company} 揽收，请注意查收。",
  "provider": "chuanglan",
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

#### DELETE /api/sms/admin/templates/{template_id}

删除指定短信模板。

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| template_id | int | 模板 ID |

**请求示例（经网关）**

```http
DELETE /api/sms/admin/templates/1 HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
```

```bash
curl -X DELETE http://localhost:8080/api/sms/admin/templates/1 \
  -H "Authorization: Bearer <access_token>"
```

**请求示例（直连）**

```http
DELETE /api/sms/admin/templates/1 HTTP/1.1
Host: localhost:8010
Authorization: Bearer <access_token>
```

```bash
curl -X DELETE http://localhost:8010/api/sms/admin/templates/1 \
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

#### GET /api/sms/admin/config

查询当前短信服务运行时配置。敏感密钥（AccessKey 等）不返回。

**请求示例（经网关）**

```http
GET /api/sms/admin/config HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
```

```bash
curl http://localhost:8080/api/sms/admin/config \
  -H "Authorization: Bearer <access_token>"
```

**请求示例（直连）**

```http
GET /api/sms/admin/config HTTP/1.1
Host: localhost:8010
Authorization: Bearer <access_token>
```

```bash
curl http://localhost:8010/api/sms/admin/config \
  -H "Authorization: Bearer <access_token>"
```

**响应示例（200 OK）**

```json
{
  "sms_provider": "chuanglan",
  "sms_provider_fallback": "",
  "sms_provider_failure_threshold": 3,
  "sms_provider_recovery_timeout": 60,
  "sms_code_ttl": 300,
  "sms_rate_limit_phone_per_minute": 1,
  "sms_rate_limit_phone_per_day": 10,
  "sms_rate_limit_ip_per_minute": 10,
  "sms_rate_limit_ip_per_day": 100,
  "sms_records_retention_days": 90
}
```

---

#### PUT /api/sms/admin/config

动态更新短信服务运行时配置，立即生效。**注意**：重启服务后将恢复为环境变量值，如需永久生效请同步更新环境变量并滚动重启服务。

**请求体**

| 字段 | 类型 | 必填 | 约束 | 说明 |
|------|------|------|------|------|
| sms_provider | string | — | — | 切换主供应商（`aliyun`/`tencent`/`chuanglan`） |
| sms_provider_fallback | string | — | — | 切换备用供应商，空字符串表示不启用 |
| sms_provider_failure_threshold | int | — | ≥ 1 | 熔断器连续失败次数阈值 |
| sms_provider_recovery_timeout | int | — | ≥ 1 | 熔断器恢复等待时间（秒） |
| sms_code_ttl | int | — | ≥ 60 | 验证码有效期（秒） |
| sms_rate_limit_phone_per_minute | int | — | ≥ 1 | 单手机号每分钟发送上限 |
| sms_rate_limit_phone_per_day | int | — | ≥ 1 | 单手机号每日发送上限 |
| sms_rate_limit_ip_per_minute | int | — | ≥ 1 | 单 IP 每分钟发送上限 |
| sms_rate_limit_ip_per_day | int | — | ≥ 1 | 单 IP 每日发送上限 |
| sms_records_retention_days | int | — | ≥ 0 | 发送记录保留天数，0 表示永久保留 |

**请求示例（经网关）**

```http
PUT /api/sms/admin/config HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "sms_provider": "aliyun",
  "sms_code_ttl": 600
}
```

```bash
curl -X PUT http://localhost:8080/api/sms/admin/config \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"sms_provider":"aliyun","sms_code_ttl":600}'
```

**请求示例（直连）**

```http
PUT /api/sms/admin/config HTTP/1.1
Host: localhost:8010
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "sms_provider": "aliyun",
  "sms_code_ttl": 600
}
```

```bash
curl -X PUT http://localhost:8010/api/sms/admin/config \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"sms_provider":"aliyun","sms_code_ttl":600}'
```

**响应示例（200 OK）**

```json
{
  "sms_provider": "aliyun",
  "sms_provider_fallback": "",
  "sms_provider_failure_threshold": 3,
  "sms_provider_recovery_timeout": 60,
  "sms_code_ttl": 600,
  "sms_rate_limit_phone_per_minute": 1,
  "sms_rate_limit_phone_per_day": 10,
  "sms_rate_limit_ip_per_minute": 10,
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
| 422 | 请求体格式错误 / 验证码无效或已过期 |
| 429 | 触发发送频率限制 |
| 500 | 服务器内部错误 |

**404 响应示例**

```json
{
  "detail": "SMS template 999 not found"
}
```

**429 响应示例**

```json
{
  "code": 40501,
  "message": "IP rate limit exceeded. Retry after 55s",
  "data": null,
  "request_id": "b1234567-89ab-cdef-0123-456789abcdef"
}
```

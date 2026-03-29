---
title: 短信服务 API
---

**Base URL（直连）**: `http://localhost:8010`
**Base URL（经网关）**: `http://localhost:8080`（网关路由前缀：`/api/sms` → sms-service）
**Content-Type**: `application/json`

---

## 目录

1. [健康检查](#健康检查)
2. [短信发送 SMS Send](#短信发送-sms-send)
3. [发送记录](#发送记录)
4. [验证码验证 SMS Verify](#验证码验证-sms-verify)
5. [短信模板管理](#短信模板管理)
6. [短信配置管理](#短信配置管理)
7. [状态枚举](#状态枚举)
8. [通用错误码](#通用错误码)

---

## 统一响应格式

所有接口均使用统一响应结构：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... },
  "request_id": "a4273592-26e4-4310-a68f-81adebeb9dbc"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务状态码，`0` 表示成功 |
| message | string | 状态描述 |
| data | object \| null | 响应数据，成功时为业务对象，失败时为 `null` |
| request_id | string | 请求追踪 ID（UUID） |

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

发送短信，支持模板变量替换。可提供 `request_id` 作为幂等键防止重复发送，可提供 `channel` 指定多租户渠道。请求到达前会依次检查手机号维度与 IP 维度的发送频率限制。

**无需认证**

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| phone | string | ✓ | 手机号（E.164 格式或本地格式） |
| template_id | string | ✓ | 短信模板标识符 |
| params | object | — | 模板变量，默认为空对象 |
| request_id | string | — | 客户端幂等键，最长 64 个字符 |
| channel | string | — | 指定渠道名称（多租户路由），最长 64 个字符；不传则使用默认供应商 |

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
  "request_id": "req-abc-001",
  "channel": "internal"
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
  "code": 0,
  "message": "success",
  "data": {
    "message_id": "1",
    "request_id": "req-abc-001",
    "status": "SENT",
    "provider": "chuanglan",
    "phone_masked": "138****8000"
  },
  "request_id": "a4273592-26e4-4310-a68f-81adebeb9dbc"
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

**认证**：需在请求头携带 `X-API-Key`。当 `SMS_CLIENT_KEYS` 为空时 auth 关闭（不需要 Key）。API Key 关联的渠道决定实际使用的供应商。

**请求头**

| 头 | 必填 | 说明 |
|----|------|------|
| X-API-Key | * | 客户端 API Key（auth 开启时必填） |

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| phone | string | ✓ | 手机号 |
| template_id | string | ✓ | 短信模板标识符 |

**请求示例**

```http
POST /api/sms/send-code HTTP/1.1
Host: localhost:8010
X-API-Key: key-business-a-001
Content-Type: application/json

{
  "phone": "13800138000",
  "template_id": "100001"
}
```

```bash
curl -X POST http://localhost:8010/api/sms/send-code \
  -H "X-API-Key: key-business-a-001" \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800138000","template_id":"100001"}'
```

**响应示例（201 Created）**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "message_id": "42",
    "request_id": null,
    "status": "SENT",
    "provider": "aliyun_phone_svc",
    "phone_masked": "138****8000"
  },
  "request_id": "c5384701-37f5-4421-b79f-92bdfec0adcd"
}
```

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 401 | API Key 无效或缺失 |
| 429 | 触发限频 |
| 502 | 供应商发送失败 |

---

## 发送记录

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
  "code": 0,
  "message": "success",
  "data": {
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
  },
  "request_id": "d6495812-48g6-5532-c80g-03ceffd1bedf"
}
```

---

### DELETE /api/sms/records/{record_id}

删除指定短信发送记录。

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| record_id | int | 记录 ID |

**请求示例**

```http
DELETE /api/sms/records/2 HTTP/1.1
Host: localhost:8010
```

```bash
curl -X DELETE http://localhost:8010/api/sms/records/2
```

**响应（204 No Content）**：无响应体。

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 404 | 记录不存在 |

**404 响应示例**

```json
{
  "code": 40504,
  "message": "SMS record 2 not found",
  "data": null,
  "request_id": "e7506923-59h7-6643-d91h-14dfgge2cfeg"
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
  "code": 0,
  "message": "success",
  "data": {
    "phone": "13800138000",
    "valid": true
  },
  "request_id": "f8617034-60i8-7754-e02i-25eghgf3dgfh"
}
```

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 422 | 验证码错误或已过期 |

**422 响应示例**

```json
{
  "code": 40502,
  "message": "invalid or expired verification code",
  "data": null,
  "request_id": "g9728145-71j9-8865-f13j-36fhihg4ehgi"
}
```

---

## 短信模板管理

### GET /api/sms/templates

查询短信模板列表，支持供应商和启用状态过滤，分页返回。

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| provider | string | — | 按供应商过滤（`aliyun`/`aliyun_phone_svc`/`tencent`/`chuanglan`） |
| is_active | bool | — | 按启用状态过滤 |
| page | int | — | 页码，默认 1 |
| size | int | — | 每页条数，默认 20，最大 100 |

**请求示例**

```http
GET /api/sms/templates?provider=chuanglan&is_active=true&page=1&size=20 HTTP/1.1
Host: localhost:8010
```

```bash
curl "http://localhost:8010/api/sms/templates?provider=chuanglan&is_active=true&page=1&size=20"
```

**响应示例（200 OK）**

```json
{
  "code": 0,
  "message": "success",
  "data": {
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
  },
  "request_id": "h0839256-82k0-9976-g24k-47gijijg5fihj"
}
```

---

### POST /api/sms/templates

创建短信模板。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| provider_template_id | string | ✓ | 供应商模板 ID，最长 64 字符 |
| name | string | ✓ | 本地模板名称，最长 128 字符 |
| content | string | ✓ | 模板内容，可包含变量占位符 |
| provider | string | ✓ | 供应商名称，最长 32 字符 |
| is_active | bool | — | 是否启用，默认 `true` |

**请求示例**

```http
POST /api/sms/templates HTTP/1.1
Host: localhost:8010
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
curl -X POST http://localhost:8010/api/sms/templates \
  -H "Content-Type: application/json" \
  -d '{"provider_template_id":"TPL_123456","name":"订单发货通知","content":"您的订单 ${orderId} 已由 ${company} 揽收，请注意查收。","provider":"chuanglan","is_active":true}'
```

**响应示例（201 Created）**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "provider_template_id": "TPL_123456",
    "name": "订单发货通知",
    "content": "您的订单 ${orderId} 已由 ${company} 揽收，请注意查收。",
    "provider": "chuanglan",
    "is_active": true,
    "created_at": "2024-06-01T10:00:00",
    "updated_at": "2024-06-01T10:00:00"
  },
  "request_id": "i1940367-93l1-0087-h35l-58hjkjkh6gjik"
}
```

---

### GET /api/sms/templates/{template_id}

获取指定短信模板详情。

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| template_id | int | 模板 ID |

**请求示例**

```http
GET /api/sms/templates/1 HTTP/1.1
Host: localhost:8010
```

```bash
curl http://localhost:8010/api/sms/templates/1
```

**响应示例（200 OK）**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "provider_template_id": "TPL_123456",
    "name": "订单发货通知",
    "content": "您的订单 ${orderId} 已由 ${company} 揽收，请注意查收。",
    "provider": "chuanglan",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  },
  "request_id": "j2051478-04m2-1198-i46m-69iklkli7hkjl"
}
```

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 404 | 模板不存在 |

**404 响应示例**

```json
{
  "code": 40503,
  "message": "SMS template 999 not found",
  "data": null,
  "request_id": "k3162589-15n3-2209-j57n-70jlmlmj8iljm"
}
```

---

### PUT /api/sms/templates/{template_id}

局部更新短信模板（仅传需修改的字段）。

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| template_id | int | 模板 ID |

**请求体**

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 新模板名称，最长 128 字符 |
| content | string | 新模板内容 |
| provider | string | 新供应商，最长 32 字符 |
| is_active | bool | 启用/禁用 |

**请求示例**

```http
PUT /api/sms/templates/1 HTTP/1.1
Host: localhost:8010
Content-Type: application/json

{
  "is_active": false
}
```

```bash
curl -X PUT http://localhost:8010/api/sms/templates/1 \
  -H "Content-Type: application/json" \
  -d '{"is_active":false}'
```

**响应示例（200 OK）**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "provider_template_id": "TPL_123456",
    "name": "订单发货通知",
    "content": "您的订单 ${orderId} 已由 ${company} 揽收，请注意查收。",
    "provider": "chuanglan",
    "is_active": false,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-06-01T10:00:00"
  },
  "request_id": "l4273690-26o4-3310-k68o-81kmnmnk9jmkn"
}
```

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 404 | 模板不存在 |

---

### DELETE /api/sms/templates/{template_id}

删除指定短信模板。

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| template_id | int | 模板 ID |

**请求示例**

```http
DELETE /api/sms/templates/1 HTTP/1.1
Host: localhost:8010
```

```bash
curl -X DELETE http://localhost:8010/api/sms/templates/1
```

**响应（204 No Content）**：无响应体。

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 404 | 模板不存在 |

---

## 短信配置管理

### GET /api/sms/config

查询当前短信服务运行时配置。密钥类字段（`access_key_secret`/`password`/`secret_key`）脱敏为 `"***"`，未配置时为空字符串。

**请求示例**

```http
GET /api/sms/config HTTP/1.1
Host: localhost:8010
```

```bash
curl http://localhost:8010/api/sms/config
```

**响应示例（200 OK）**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "sms_provider": "chuanglan",
    "sms_provider_fallback": "",
    "sms_provider_failure_threshold": 3,
    "sms_provider_recovery_timeout": 60,
    "sms_code_ttl": 300,
    "sms_rate_limit_phone_per_minute": 1,
    "sms_rate_limit_phone_per_day": 10,
    "sms_rate_limit_ip_per_minute": 10,
    "sms_rate_limit_ip_per_day": 100,
    "sms_records_retention_days": 90,
    "sms_channels": {
      "business_a": {
        "provider": "aliyun_phone_svc",
        "access_key_id": "LTAIxxxxxx",
        "access_key_secret": "***",
        "sign_name": "A业务",
        "endpoint": "dypnsapi.aliyuncs.com"
      }
    },
    "sms_client_keys": {
      "key-business-a-001": "business_a"
    },
    "chuanglan": {
      "account": "ACC123",
      "password": "***",
      "api_url": "https://smssh1.253.com/msg/v1/send/json"
    },
    "aliyun": {
      "access_key_id": "LTAIxxxxxx",
      "access_key_secret": "***",
      "sign_name": "你的签名",
      "endpoint": "dysmsapi.aliyuncs.com"
    },
    "aliyun_phone_svc": {
      "access_key_id": "LTAIxxxxxx",
      "access_key_secret": "***",
      "sign_name": "你的签名",
      "endpoint": "dypnsapi.aliyuncs.com"
    },
    "tencent": {
      "secret_id": "AKIDxxxxxx",
      "secret_key": "***",
      "app_id": "1400000000",
      "sign_name": "你的签名"
    }
  },
  "request_id": "m5384701-37p5-4421-l79p-92lnonol0knlo"
}
```

---

### PUT /api/sms/config

动态更新短信服务运行时配置，立即生效并**持久化到数据库**，服务重启后自动恢复。**SMS 供应商配置（凭据、限频、熔断器参数等）不通过环境变量管理，此接口是唯一的配置入口。**

`sms_channels` 和 `sms_client_keys` 均为**增量合并**：传入字段将被新增或覆盖，未传字段保持不变；将值设为 `null` 可删除该条目。供应商凭据字段（`chuanglan`/`aliyun`/`aliyun_phone_svc`/`tencent`）同样为部分更新，只修改传入的子字段。

**请求体（全部字段可选）**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| sms_provider | string | — | 切换主供应商（`aliyun`/`aliyun_phone_svc`/`tencent`/`chuanglan`） |
| sms_provider_fallback | string | — | 备用供应商，空字符串表示不启用 |
| sms_provider_failure_threshold | int | ≥ 1 | 熔断器连续失败次数阈值 |
| sms_provider_recovery_timeout | int | ≥ 1 | 熔断器恢复等待时间（秒） |
| sms_code_ttl | int | ≥ 60 | 验证码有效期（秒） |
| sms_rate_limit_phone_per_minute | int | ≥ 1 | 单手机号每分钟发送上限 |
| sms_rate_limit_phone_per_day | int | ≥ 1 | 单手机号每日发送上限 |
| sms_rate_limit_ip_per_minute | int | ≥ 1 | 单 IP 每分钟发送上限 |
| sms_rate_limit_ip_per_day | int | ≥ 1 | 单 IP 每日发送上限 |
| sms_records_retention_days | int | ≥ 0 | 发送记录保留天数，0 表示永久保留 |
| sms_channels | object | — | 渠道配置（增量合并，值为 `null` 则删除该渠道） |
| sms_client_keys | object | — | 客户端 Key 映射（增量合并，值为 `null` 则删除该 Key） |
| chuanglan | object | — | 创蓝云凭据（部分更新） |
| aliyun | object | — | 阿里云短信凭据（部分更新） |
| aliyun_phone_svc | object | — | 阿里云号码认证凭据（部分更新） |
| tencent | object | — | 腾讯云凭据（部分更新） |

**`sms_channels` 渠道配置字段**

| 字段 | 类型 | 说明 |
|------|------|------|
| provider | string | 供应商标识（`aliyun` / `aliyun_phone_svc` / `tencent` / `chuanglan`） |
| access_key_id | string | Access Key ID |
| access_key_secret | string | Access Key Secret |
| sign_name | string | 短信签名 |
| endpoint | string | API Endpoint（留空使用默认值） |

**`chuanglan` 凭据字段**

| 字段 | 类型 | 说明 |
|------|------|------|
| account | string | 创蓝云账号 |
| password | string | 创蓝云密码 |
| api_url | string | API 地址 |

**`aliyun` / `aliyun_phone_svc` 凭据字段**

| 字段 | 类型 | 说明 |
|------|------|------|
| access_key_id | string | Access Key ID |
| access_key_secret | string | Access Key Secret |
| sign_name | string | 短信签名 |
| endpoint | string | API Endpoint（留空使用默认值） |

**`tencent` 凭据字段**

| 字段 | 类型 | 说明 |
|------|------|------|
| secret_id | string | SecretId |
| secret_key | string | SecretKey |
| app_id | string | SdkAppId |
| sign_name | string | 短信签名 |

**示例：新增渠道和客户端 Key**

```http
PUT /api/sms/config HTTP/1.1
Host: localhost:8010
Content-Type: application/json

{
  "sms_channels": {
    "business_a": {
      "provider": "aliyun_phone_svc",
      "access_key_id": "LTAIxxxxxx",
      "access_key_secret": "secret-a",
      "sign_name": "A业务",
      "endpoint": "dypnsapi.aliyuncs.com"
    }
  },
  "sms_client_keys": {
    "key-business-a-001": "business_a"
  }
}
```

**示例：更新供应商凭据**

```http
PUT /api/sms/config HTTP/1.1
Host: localhost:8010
Content-Type: application/json

{
  "sms_provider": "aliyun_phone_svc",
  "aliyun_phone_svc": {
    "access_key_id": "LTAIxxxxxx",
    "access_key_secret": "your_secret",
    "sign_name": "你的签名",
    "endpoint": "dypnsapi.aliyuncs.com"
  }
}
```

**示例：删除渠道或 Key**

```http
PUT /api/sms/config HTTP/1.1
Host: localhost:8010
Content-Type: application/json

{
  "sms_channels": { "business_a": null },
  "sms_client_keys": { "key-business-a-001": null }
}
```

**响应示例（200 OK）**：同 `GET /api/sms/config` 响应结构。

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

| 业务码 | HTTP 状态码 | 说明 |
|--------|------------|------|
| 0 | 200 / 201 | 成功 |
| 40011 | 400 / 422 | 请求参数校验失败 |
| 40500 | 502 | 短信供应商调用失败 |
| 40501 | 429 | 触发发送频率限制 |
| 40502 | 422 | 验证码无效或已过期 |
| 40503 | 404 | 短信模板不存在 |
| 40504 | 404 | 短信记录不存在 |
| 50000 | 500 | 服务器内部错误 |

**通用错误响应结构**

```json
{
  "code": 40503,
  "message": "SMS template 999 not found",
  "data": null,
  "request_id": "a4273592-26e4-4310-a68f-81adebeb9dbc"
}
```

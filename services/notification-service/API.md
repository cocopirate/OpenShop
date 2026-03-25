# Notification Service — 接口文档

**Base URL（直连）**: `http://localhost:8009`  
**Base URL（经网关）**: `http://localhost:8080`  
**Content-Type**: `application/json`  
**认证方式**: `Authorization: Bearer <access_token>`

通知服务作为业务语义层，负责站内信、App Push、邮件及短信的统一发送调度。对于短信渠道，通知服务将请求同步转发至 sms-service（能力层）处理。

---

## 目录

1. [健康检查](#健康检查)
2. [发送通知](#发送通知)
3. [站内信](#站内信)
4. [渠道说明](#渠道说明)
5. [通用错误码](#通用错误码)

---

## 健康检查

### GET /health

服务存活检查。

**无需认证**

**请求示例**

```http
GET /health HTTP/1.1
Host: localhost:8009
```

```bash
curl http://localhost:8009/health
```

**响应示例（200 OK）**

```json
{
  "status": "ok"
}
```

---

### GET /health/ready

Kubernetes Readiness Probe，服务就绪后返回 200。

**无需认证**

**请求示例**

```http
GET /health/ready HTTP/1.1
Host: localhost:8009
```

```bash
curl http://localhost:8009/health/ready
```

**响应示例（200 OK）**

```json
{
  "status": "ready"
}
```

---

## 发送通知

### POST /api/v1/notifications/send

统一通知发送入口，支持 `push`、`email`、`in_app`、`sms` 四种渠道。

- **短信渠道（`sms`）**：同步调用 sms-service，结果直接透传。
- **其他渠道（`push`/`email`/`in_app`）**：入队异步处理，立即返回 `queued` 状态。

**需要认证**

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string | ✓ | 目标用户 ID |
| channel | string | ✓ | 通知渠道：`push` / `email` / `in_app` / `sms` |
| title | string | ✓ | 通知标题 |
| content | string | ✓ | 通知正文 |
| template_id | string | — | 模板标识符，`sms` 渠道时必填 |
| phone | string | — | 手机号，`sms` 渠道时必填 |
| sms_params | object | — | 短信模板变量，仅 `sms` 渠道使用 |
| request_id | string | — | 幂等键，仅 `sms` 渠道使用 |

---

#### 请求示例（短信渠道）

```http
POST /api/v1/notifications/send HTTP/1.1
Host: localhost:8009
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "user_id": "u_123",
  "channel": "sms",
  "title": "订单发货通知",
  "content": "您的订单已发货",
  "template_id": "SMS_ORDER_SHIPPED",
  "phone": "13800138000",
  "sms_params": {
    "orderId": "ORD-001",
    "company": "顺丰速运"
  },
  "request_id": "req-abc-001"
}
```

```bash
curl -X POST http://localhost:8009/api/v1/notifications/send \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u_123","channel":"sms","title":"订单发货通知","content":"您的订单已发货","template_id":"SMS_ORDER_SHIPPED","phone":"13800138000","sms_params":{"orderId":"ORD-001","company":"顺丰速运"},"request_id":"req-abc-001"}'
```

**响应示例（200 OK — 短信渠道）**

```json
{
  "notification_id": "aliyun-msg-20240601-001",
  "channel": "sms",
  "status": "SENT",
  "provider": "aliyun"
}
```

---

#### 请求示例（站内信渠道）

```http
POST /api/v1/notifications/send HTTP/1.1
Host: localhost:8009
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "user_id": "u_123",
  "channel": "in_app",
  "title": "您有一条新消息",
  "content": "您的订单 ORD-001 已发货，请关注物流动态。"
}
```

```bash
curl -X POST http://localhost:8009/api/v1/notifications/send \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u_123","channel":"in_app","title":"您有一条新消息","content":"您的订单 ORD-001 已发货，请关注物流动态。"}'
```

**响应示例（200 OK — 异步渠道）**

```json
{
  "notification_id": "NOTIF-20240601-001",
  "channel": "in_app",
  "status": "queued"
}
```

---

#### 请求示例（Push 渠道）

```http
POST /api/v1/notifications/send HTTP/1.1
Host: localhost:8009
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "user_id": "u_123",
  "channel": "push",
  "title": "促销活动提醒",
  "content": "限时折扣进行中，快来抢购！"
}
```

```bash
curl -X POST http://localhost:8009/api/v1/notifications/send \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u_123","channel":"push","title":"促销活动提醒","content":"限时折扣进行中，快来抢购！"}'
```

**响应示例（200 OK — Push 渠道）**

```json
{
  "notification_id": "NOTIF-20240601-002",
  "channel": "push",
  "status": "queued"
}
```

---

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 401 | 未携带 Token 或 Token 无效 |
| 422 | 请求体格式错误，或短信渠道缺少必填字段 |
| 502 | sms-service 返回错误或无法连接 |

**422 响应示例（短信渠道缺少 phone）**

```json
{
  "detail": "phone is required when channel is sms"
}
```

**422 响应示例（短信渠道缺少 template_id）**

```json
{
  "detail": "template_id is required when channel is sms"
}
```

**502 响应示例（sms-service 不可用）**

```json
{
  "detail": "failed to reach sms-service"
}
```

---

## 站内信

### GET /api/v1/notifications/{user_id}/inbox

获取指定用户的站内信列表，支持分页。

**需要认证**

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| user_id | string | 目标用户 ID |

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | — | 页码，默认 1 |
| size | int | — | 每页条数，默认 20 |

**请求示例**

```http
GET /api/v1/notifications/u_123/inbox?page=1&size=20 HTTP/1.1
Host: localhost:8009
Authorization: Bearer <access_token>
```

```bash
curl "http://localhost:8009/api/v1/notifications/u_123/inbox?page=1&size=20" \
  -H "Authorization: Bearer <access_token>"
```

**响应示例（200 OK）**

```json
{
  "user_id": "u_123",
  "items": [],
  "total": 0
}
```

---

### PUT /api/v1/notifications/{notification_id}/read

将指定站内信标记为已读。

**需要认证**

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| notification_id | string | 通知 ID |

**请求示例**

```http
PUT /api/v1/notifications/NOTIF-20240601-001/read HTTP/1.1
Host: localhost:8009
Authorization: Bearer <access_token>
```

```bash
curl -X PUT http://localhost:8009/api/v1/notifications/NOTIF-20240601-001/read \
  -H "Authorization: Bearer <access_token>"
```

**响应示例（200 OK）**

```json
{
  "notification_id": "NOTIF-20240601-001",
  "read": true
}
```

---

## 渠道说明

| channel | 说明 | 处理方式 | 下游依赖 |
|---------|------|---------|---------|
| `sms` | 短信通知 | **同步** HTTP 调用 sms-service | sms-service（:8010） |
| `push` | App Push 通知（FCM/APNs） | 异步队列 | Kafka |
| `email` | 邮件通知 | 异步队列 | Kafka |
| `in_app` | 站内信 | 异步队列 | Kafka |

### 短信通知链路

```
Client（App / Web）
   ↓  POST /app/v1/notifications/send-sms
BFF（app-bff）
   ↓  POST /api/v1/notifications/send  { channel: "sms", ... }
API Gateway（:8080）
   ↓  路由转发
notification-service（:8009）  ← 业务语义层：决定何时发通知、发什么
   ↓  POST /api/v1/sms/send
sms-service（:8010）           ← 能力层：负责与供应商对接
   ↓
短信供应商（阿里云 / 腾讯云 / 创蓝）
```

---

## 通用错误码

| 状态码 | 说明 |
|--------|------|
| 400 | 请求参数校验失败 |
| 401 | 未携带 Token、Token 无效或已过期 |
| 403 | 缺少所需权限 |
| 422 | 请求体格式错误或业务参数校验失败 |
| 502 | 下游能力服务（sms-service）不可用或返回错误 |
| 500 | 服务器内部错误 |

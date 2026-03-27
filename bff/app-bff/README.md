# App BFF (Backend For Frontend)

面向移动端 App 和微信小程序的 BFF 服务，聚合多个领域服务接口，提供适配移动端的响应格式。

## 技术选型

- **框架**: FastAPI (Python 3.11+)
- **HTTP 客户端**: httpx (异步)
- **缓存**: Redis (aioredis)

## 职责

- 接口聚合：将多个下游服务的数据合并为一次响应
- 数据裁剪：按移动端需求精简响应字段
- 缓存加速：对热点数据做 Redis 缓存
- 格式适配：统一返回格式 `{code, message, data}`

## 主要聚合接口

| 接口 | 聚合来源 |
|------|---------|
| `GET /app/v1/home` | product-service + promotion-service |
| `GET /app/v1/orders/{id}` | order-service + product-service |
| `POST /app/v1/checkout` | order-orchestration |
| `GET /app/v1/profile` | consumer-service + merchant-service |
| `POST /app/v1/notifications/send-sms` | notification-service |

### 发送短信通知 – 请求示例

```
POST /app/v1/notifications/send-sms
Authorization: Bearer <token>

{
  "phone": "13800138000",
  "template_id": "SMS_VERIFY_CODE",
  "params": { "code": "123456" }
}
```

BFF 将请求转发至 API Gateway，再路由到 notification-service：

```
App
 ↓  POST /app/v1/notifications/send-sms
app-bff（:8090）
 ↓  POST /api/v1/notifications/send  { channel: "sms", ... }
API Gateway（:8080）
 ↓  路由转发
notification-service（:8009）
 ↓  POST /api/v1/sms/send
sms-service（:8010）
 ↓
短信供应商（阿里云 / 腾讯云 / 创蓝）
```

## 端口

- 服务端口: **8090**

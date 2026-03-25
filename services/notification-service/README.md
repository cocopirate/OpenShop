# notification-service（通知服务）

负责站内信、Push 通知、邮件及短信的统一发送。作为业务语义层，根据通知类型将请求路由到对应的能力服务（如 sms-service）。

## 职责

- 站内消息推送
- App Push 通知（FCM/APNs）
- 邮件发送
- **短信通知**（通过 sms-service 能力层发送）

## 短信通知链路

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

## 主要接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `POST /api/v1/notifications/send` | POST | 发送通知（支持 push / email / in_app / sms 四种渠道） |
| `GET /api/v1/notifications/{user_id}/inbox` | GET | 获取用户站内信 |
| `PUT /api/v1/notifications/{notification_id}/read` | PUT | 标记已读 |

### 发送短信通知 – 请求示例

```json
POST /api/v1/notifications/send
{
  "user_id": "u_123",
  "channel": "sms",
  "title": "订单发货通知",
  "content": "您的订单已发货",
  "template_id": "SMS_ORDER_SHIPPED",
  "phone": "13800138000",
  "sms_params": { "orderId": "ORD-001", "company": "顺丰速运" },
  "request_id": "req-abc-001"
}
```

### 渠道说明

| channel | 说明 | 下游依赖 |
|---------|------|---------|
| `push` | App Push 通知（FCM/APNs） | 异步队列（Kafka） |
| `email` | 邮件通知 | 异步队列（Kafka） |
| `in_app` | 站内信 | 异步队列（Kafka） |
| `sms` | 短信通知 | **sms-service（同步 HTTP 调用）** |

## 数据模型

- Notification
- NotificationTemplate
- NotificationLog

## 依赖服务

- **sms-service**（`http://sms-service:8010`）– 短信渠道的下游能力服务
- Kafka（消费各服务产生的通知事件）

## 配置项

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `SMS_SERVICE_URL` | `http://sms-service:8010` | sms-service 地址 |
| `DATABASE_URL` | – | PostgreSQL 连接串 |
| `REDIS_URL` | – | Redis 连接串 |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka 地址 |

## 端口

- 服务端口: **8009**

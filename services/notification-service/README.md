# notification-service（通知服务）

负责站内信、Push 通知及邮件的统一发送。

## 职责

- 站内消息推送
- App Push 通知（FCM/APNs）
- 邮件发送

## 主要接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `POST /api/v1/notifications/send` | POST | 发送通知 |
| `GET /api/v1/notifications/{user_id}/inbox` | GET | 获取用户站内信 |
| `PUT /api/v1/notifications/{notification_id}/read` | PUT | 标记已读 |

## 数据模型

- Notification
- NotificationTemplate
- NotificationLog

## 依赖服务

- sms-service（短信发送）
- Kafka（消费各服务产生的通知事件）

## 端口

- 服务端口: **8009**

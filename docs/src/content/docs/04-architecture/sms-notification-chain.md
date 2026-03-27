---
title: 短信通知链路
---

本文以"发送短信验证码 / 订单通知"为例，说明 Client → BFF → API Gateway → notification-service → sms-service → 供应商的完整调用链路。

## 链路全景

```
Client（App / Web）
   │  POST /app/v1/notifications/send-sms
   ▼
BFF（app-bff :8090）
   │  聚合、鉴权、格式转换
   │  POST /api/v1/notifications/send  { channel: "sms", phone, template_id, sms_params }
   ▼
API Gateway（:8080）
   │  JWT 校验 + 路由转发（/api/v1/notifications/** → notification-service:8009）
   ▼
notification-service（:8009）  ── 业务语义层
   │  决定何时发、发什么渠道
   │  POST /api/v1/sms/send  { phone, template_id, params }
   ▼
sms-service（:8010）           ── 能力层
   │  熔断器 / 限流 / 幂等性
   │  选择供应商（SMS_PROVIDER + SMS_PROVIDER_FALLBACK）
   ▼
短信供应商
   ├── 阿里云（dysmsapi.aliyuncs.com）
   ├── 腾讯云（sms.tencentcloudapi.com）
   └── 创蓝（smssh1.253.com）
```

## 请求示例

**① App 调用 BFF**

```http
POST /app/v1/notifications/send-sms
Authorization: Bearer <user_access_token>
Content-Type: application/json

{
  "phone": "13800138000",
  "template_id": "SMS_ORDER_SHIPPED",
  "params": { "orderId": "ORD-20240101", "company": "顺丰速运" }
}
```

**② BFF 转发给 notification-service（经 API Gateway）**

```http
POST /api/v1/notifications/send
Content-Type: application/json

{
  "user_id": "u_123",
  "channel": "sms",
  "title": "订单发货通知",
  "content": "您的订单已发货",
  "template_id": "SMS_ORDER_SHIPPED",
  "phone": "13800138000",
  "sms_params": { "orderId": "ORD-20240101", "company": "顺丰速运" },
  "request_id": "req-bff-abc-001"
}
```

**③ notification-service 调用 sms-service**

```http
POST /api/v1/sms/send
Content-Type: application/json

{
  "phone": "13800138000",
  "template_id": "SMS_ORDER_SHIPPED",
  "params": { "orderId": "ORD-20240101", "company": "顺丰速运" },
  "request_id": "req-bff-abc-001"
}
```

**④ sms-service 响应**

```json
{
  "message_id": "42",
  "request_id": "req-bff-abc-001",
  "status": "sent",
  "provider": "aliyun",
  "phone_masked": "138****8000"
}
```

## 关键设计决策

| 关注点 | 方案 |
|--------|------|
| **幂等性** | `request_id` 贯穿全链路；sms-service 用 Redis 去重（TTL 24h） |
| **限流** | sms-service 对手机号（1次/分钟，10次/天）和 IP（10次/分钟）独立限流 |
| **熔断** | sms-service 内置熔断器；主供应商故障时自动切换到 `SMS_PROVIDER_FALLBACK` |
| **可观测性** | sms-service 暴露 Prometheus 指标（`sms_send_total`、`sms_send_latency_seconds`）；structlog 结构化日志 |
| **隐私保护** | 手机号在日志中脱敏（`138****8000`）；数据库仅存储脱敏后的 `phone_masked` 用于查询 |
| **数据保留** | `SMS_RECORDS_RETENTION_DAYS`（默认 90 天）定期清理历史记录 |

## 供应商切换

sms-service 支持运行时通过环境变量切换供应商，无需重新部署代码：

```bash
# 主供应商设为腾讯云，备用创蓝
SMS_PROVIDER=tencent
SMS_PROVIDER_FALLBACK=chuanglan
SMS_PROVIDER_FAILURE_THRESHOLD=3      # 连续失败 3 次触发熔断
SMS_PROVIDER_RECOVERY_TIMEOUT=60      # 60 秒后尝试恢复
```

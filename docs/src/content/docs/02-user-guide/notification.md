---
title: 通知系统
---

## 通知渠道

OpenShop 目前支持以下通知渠道：

| 渠道 | 说明 |
|------|------|
| SMS | 短信通知，通过短信供应商发送 |
| 站内信 | 平台内通知（规划中） |
| Push | App 推送（规划中） |

## 短信通知链路

```
客户端 / 业务服务
    │
    ▼
notification-service（业务语义层，决定何时发、发什么）
    │  POST /api/v1/sms/send
    ▼
sms-service（能力层，熔断/限流/幂等/供应商管理）
    │
    ▼
短信供应商（阿里云 / 腾讯云 / 创蓝）
```

## 触发通知的业务事件

| 事件 | 通知内容 |
|------|----------|
| `customer.registered` | 欢迎短信 |
| `order.created` | 下单成功通知 |
| `order.paid` | 支付成功通知 |
| `order.shipped` | 发货通知（含快递单号） |
| `order.cancelled` | 订单取消通知 |
| `aftersale.approved` | 售后审核通过通知 |

## 发送短信 API

通过 notification-service 发送通知（经 API Gateway）：

```http
POST /api/v1/notifications/send
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "user_id": "u_123",
  "channel": "sms",
  "phone": "13800138000",
  "template_id": "SMS_ORDER_SHIPPED",
  "sms_params": {
    "orderId": "ORD-20240101",
    "company": "顺丰速运"
  },
  "request_id": "req-bff-abc-001"
}
```

## 幂等性保证

- 每次发送请求需携带唯一 `request_id`
- sms-service 使用 Redis 对 `request_id` 去重（TTL 24h）
- 相同 `request_id` 的重复请求直接返回首次结果

## 限流规则

| 维度 | 限制 |
|------|------|
| 单手机号每分钟 | 1 次 |
| 单手机号每天 | 10 次 |
| 单 IP 每分钟 | 10 次 |

超出限制返回 `429 Too Many Requests`。

## 供应商切换

sms-service 支持多供应商，可通过环境变量在启动时切换，也支持运行时通过管理 API 动态切换：

```bash
SMS_PROVIDER=aliyun            # 主供应商
SMS_PROVIDER_FALLBACK=tencent  # 备用供应商
```

详见 [短信服务 API 参考](../03-api-reference/sms.md)。

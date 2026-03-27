---
title: 短信服务 API
---

> 以下接口由 sms-service（:8010）提供，管理接口前缀 `/api/v1/admin`，需管理员权限。

## 发送短信

由 notification-service 内部调用，不对外暴露：

```http
POST /api/v1/sms/send
Content-Type: application/json

{
  "phone": "13800138000",
  "template_id": "SMS_ORDER_SHIPPED",
  "params": {
    "orderId": "ORD-20240101",
    "company": "顺丰速运"
  },
  "request_id": "req-bff-abc-001"
}
```

**响应：**

```json
{
  "message_id": "42",
  "request_id": "req-bff-abc-001",
  "status": "sent",
  "provider": "aliyun",
  "phone_masked": "138****8000"
}
```

## 短信发送记录

### 查询发送记录

```http
GET /api/v1/admin/sms/records?phone=138****8000&status=SENT&page=1&size=20
Authorization: Bearer <admin_token>
```

**查询参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| phone | string | 手机号精确匹配（可选） |
| start_time | string (ISO 8601) | 开始时间（可选） |
| end_time | string (ISO 8601) | 结束时间（可选） |
| status | enum | PENDING / SENT / DELIVERED / FAILED（可选） |
| page | int | 页码，默认 1 |
| size | int | 每页条数，默认 20，最大 100 |

### 删除发送记录

```http
DELETE /api/v1/admin/sms/records/{id}
Authorization: Bearer <admin_token>
```

## 短信模板管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/admin/sms/templates` | 查询模板列表 |
| POST | `/api/v1/admin/sms/templates` | 创建模板 |
| GET | `/api/v1/admin/sms/templates/{id}` | 获取模板详情 |
| PUT | `/api/v1/admin/sms/templates/{id}` | 更新模板 |
| DELETE | `/api/v1/admin/sms/templates/{id}` | 删除模板 |

**创建/更新模板请求体：**

| 字段 | 类型 | 说明 |
|------|------|------|
| provider_template_id | string (max 64) | 供应商模板 ID（创建时必填） |
| name | string (max 128) | 模板本地名称 |
| content | string | 模板内容（含变量占位符） |
| provider | string | 供应商（aliyun / tencent / chuanglan） |
| is_active | bool | 是否启用，默认 true |

## 运行时配置

### 查询当前配置

```http
GET /api/v1/admin/sms/config
Authorization: Bearer <admin_token>
```

### 动态更新配置

```http
PUT /api/v1/admin/sms/config
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "sms_provider": "tencent",
  "sms_provider_fallback": "chuanglan",
  "sms_provider_failure_threshold": 3,
  "sms_provider_recovery_timeout": 60,
  "sms_code_ttl": 300,
  "sms_rate_limit_phone_per_minute": 1,
  "sms_rate_limit_phone_per_day": 10
}
```

> **注意**：运行时更新的配置在服务重启后恢复为环境变量值。

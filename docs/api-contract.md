# API 契约文档

## 统一响应格式

所有 API 返回如下格式：

```json
{
  "code": 0,
  "message": "success",
  "data": { },
  "request_id": "uuid"
}
```

错误响应：

```json
{
  "code": 40001,
  "message": "用户不存在",
  "data": null,
  "request_id": "uuid"
}
```

## 错误码规范

| 错误码范围 | 说明 |
|-----------|------|
| 0 | 成功 |
| 40001-40099 | 用户相关错误 |
| 40100-40199 | 商品相关错误 |
| 40200-40299 | 订单相关错误 |
| 40300-40399 | 库存相关错误 |
| 40400-40499 | 促销相关错误 |
| 40500-40599 | 短信相关错误 |
| 50000-50099 | 服务内部错误 |

## JWT 鉴权

所有需要鉴权的接口需在 Header 中携带：

```
Authorization: Bearer <access_token>
```

Token 由 auth-service 颁发，API Gateway 负责校验。

## 分页约定

分页请求参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | int | 1 | 页码（从 1 开始） |
| size | int | 20 | 每页条数 |

分页响应：

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "size": 20
}
```

## 各服务 Swagger UI

本地开发时，各服务文档地址：

| 服务 | Swagger UI |
|------|-----------|
| api-gateway | http://localhost:8080/docs |
| app-bff | http://localhost:8090/docs |
| admin-bff | http://localhost:8091/docs |
| order-orchestration | http://localhost:8100/docs |
| auth-service | http://localhost:8000/docs |
| admin-service | http://localhost:8012/docs |
| consumer-service | http://localhost:8001/docs |
| merchant-service | http://localhost:8002/docs |
| product-service | http://localhost:8003/docs |
| inventory-service | http://localhost:8004/docs |
| order-service | http://localhost:8005/docs |
| aftersale-service | http://localhost:8006/docs |
| promotion-service | http://localhost:8007/docs |
| location-service | http://localhost:8008/docs |
| notification-service | http://localhost:8009/docs |
| sms-service | http://localhost:8010/docs |
| virtual-number-service | http://localhost:8011/docs |

## 短信管理后台接口（sms-service Admin API）

以下接口由 sms-service（端口 8010）提供，前缀 `/api/v1/admin`，鉴权由 API Gateway
的 RBAC 层负责（仅允许管理员角色通过）。

### 短信发送记录

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/admin/sms/records` | 查询发送记录（支持 phone/start_time/end_time/status 过滤 + 分页） |
| DELETE | `/api/v1/admin/sms/records/{id}` | 删除指定发送记录（404 当记录不存在） |

**GET 查询参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| phone | string | 手机号精确匹配（可选） |
| start_time | string (ISO 8601) | 开始时间（可选） |
| end_time | string (ISO 8601) | 结束时间（可选） |
| status | enum | PENDING / SENT / DELIVERED / FAILED（可选） |
| page | int | 页码，默认 1 |
| size | int | 每页条数，默认 20，最大 100 |

### 短信模板

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/admin/sms/templates` | 查询模板列表（支持 provider/is_active 过滤 + 分页） |
| POST | `/api/v1/admin/sms/templates` | 创建模板（201 Created） |
| GET | `/api/v1/admin/sms/templates/{id}` | 获取模板详情（404 当不存在） |
| PUT | `/api/v1/admin/sms/templates/{id}` | 局部更新模板（404 当不存在） |
| DELETE | `/api/v1/admin/sms/templates/{id}` | 删除模板（204 No Content，404 当不存在） |

**POST/PUT 请求体（SmsTemplateCreate / SmsTemplateUpdate）**

| 字段 | 类型 | 说明 |
|------|------|------|
| provider_template_id | string（max 64） | 供应商模板 ID（仅 POST 必填） |
| name | string（max 128） | 模板本地名称 |
| content | string | 模板内容（含变量占位符） |
| provider | string（max 32） | 供应商（aliyun / tencent / chuanglan） |
| is_active | bool | 是否启用，默认 true |

### 短信配置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/admin/sms/config` | 查询当前运行时配置（不含敏感密钥） |
| PUT | `/api/v1/admin/sms/config` | 动态更新运行时配置（重启后恢复至环境变量值） |

**PUT 请求体（SmsConfigUpdate，所有字段均可选）**

| 字段 | 类型 | 说明 |
|------|------|------|
| sms_provider | string | 切换活跃供应商 |
| sms_provider_fallback | string | 切换备用供应商 |
| sms_provider_failure_threshold | int (≥1) | 熔断器连续失败阈值 |
| sms_provider_recovery_timeout | int (≥1) | 熔断器恢复等待时间（秒） |
| sms_code_ttl | int (≥60) | 验证码有效期（秒） |
| sms_rate_limit_phone_per_minute | int (≥1) | 单手机号每分钟限频 |
| sms_rate_limit_phone_per_day | int (≥1) | 单手机号每日限频 |
| sms_rate_limit_ip_per_minute | int (≥1) | 单 IP 每分钟限频 |
| sms_rate_limit_ip_per_day | int (≥1) | 单 IP 每日限频 |
| sms_records_retention_days | int (≥0) | 发送记录保留天数（0 = 永久保留） |

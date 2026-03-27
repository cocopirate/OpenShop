# API 网关

## 职责

API Gateway 是所有外部请求的唯一入口，负责：

1. **JWT 鉴权**：验证 Token 签名，检查 Redis 用户状态与权限版本
2. **路由转发**：根据请求路径转发到对应的上游服务
3. **限流**：按 IP 和用户维度进行请求限速（slowapi）
4. **请求日志**：为每个请求注入唯一 `request_id`，写入结构化日志

## 路由规则

| 路径前缀 | 上游服务 |
|---------|---------|
| `/api/auth/**` | auth-service:8000 |
| `/api/admins/**` | admin-service:8012 |
| `/api/roles/**` | admin-service:8012 |
| `/api/permissions/**` | admin-service:8012 |
| `/api/v1/users/**` | consumer-service:8001 |
| `/api/v1/merchants/**` | merchant-service:8002 |
| `/api/v1/products/**` | product-service:8003 |
| `/api/v1/inventory/**` | inventory-service:8004 |
| `/api/v1/orders/**` | order-service:8005 |
| `/api/v1/aftersale/**` | aftersale-service:8006 |
| `/api/v1/promotions/**` | promotion-service:8007 |
| `/api/v1/locations/**` | location-service:8008 |
| `/api/v1/notifications/**` | notification-service:8009 |
| `/api/v1/sms/**` | sms-service:8010 |
| `/api/v1/orchestration/**` | order-orchestration:8100 |

## 短信通知完整链路示例

```
Client（App / Web）
   │  POST /app/v1/notifications/send-sms
   ▼
App BFF（:8090）
   │  聚合、鉴权、格式转换
   │  POST /api/v1/notifications/send
   ▼
API Gateway（:8080）
   │  JWT 校验 + 路由转发
   ▼
notification-service（:8009）
   │  POST /api/v1/sms/send
   ▼
sms-service（:8010）
   │  熔断器 / 限流 / 幂等性
   ▼
短信供应商（阿里云 / 腾讯云 / 创蓝）
```

## 健康检查

```http
GET /health
```

```json
{"status": "ok"}
```

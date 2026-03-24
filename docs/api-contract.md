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
| 50000-50099 | 服务内部错误 |

## JWT 鉴权

所有需要鉴权的接口需在 Header 中携带：

```
Authorization: Bearer <access_token>
```

Token 由 user-service 颁发，API Gateway 负责校验。

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
| user-service | http://localhost:8001/docs |
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

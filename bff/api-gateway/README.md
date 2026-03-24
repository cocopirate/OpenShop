# API Gateway (BFF)

## 职责

作为所有客户端（App、Web、小程序）的统一入口，负责：

- 路由转发到各微服务
- 身份认证 / JWT 校验
- 限流、熔断
- 请求聚合（BFF 模式）

## 技术选型

- Spring Cloud Gateway / Kong / Nginx

## 路由规则

| 路径前缀 | 转发目标服务 |
|---------|------------|
| `/api/orders/**` | order-service |
| `/api/inventory/**` | inventory-service |
| `/api/users/**` | user-service |
| `/api/communication/**` | communication-service |
| `/api/map/**` | map-service |
| `/api/privacy/**` | privacy-number-service |

## 目录结构

```
api-gateway/
├── src/
│   ├── filters/
│   ├── routes/
│   └── config/
├── test/
└── README.md
```
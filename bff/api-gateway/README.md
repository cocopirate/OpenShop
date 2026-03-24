# API Gateway

统一入口网关，基于 FastAPI 实现，负责路由转发、JWT 鉴权、限流与熔断。

## 技术选型

- **框架**: FastAPI (Python 3.11+)
- **鉴权**: JWT (python-jose)
- **限流**: slowapi
- **反向代理**: httpx (异步 HTTP 客户端)

## 职责

- 统一入口：所有客户端（App、Web、小程序）流量经此进入
- JWT 校验：验证 Access Token，拒绝未授权请求
- 路由转发：将请求代理到对应的下游服务
- 限流熔断：保护后端服务免受流量冲击
- 请求日志：记录所有入站请求

## 路由规则

| 路径前缀 | 转发目标服务 |
|---------|------------|
| `/api/v1/users/**` | user-service:8001 |
| `/api/v1/merchants/**` | merchant-service:8002 |
| `/api/v1/products/**` | product-service:8003 |
| `/api/v1/inventory/**` | inventory-service:8004 |
| `/api/v1/orders/**` | order-service:8005 |
| `/api/v1/aftersale/**` | aftersale-service:8006 |
| `/api/v1/promotions/**` | promotion-service:8007 |
| `/api/v1/locations/**` | location-service:8008 |
| `/api/v1/notifications/**` | notification-service:8009 |

## 目录结构

```
api-gateway/
├── app/
│   ├── main.py           # FastAPI 应用入口
│   ├── api/
│   │   └── v1/
│   │       └── router.py # 路由聚合
│   ├── core/
│   │   ├── config.py     # 配置管理
│   │   └── auth.py       # JWT 鉴权中间件
│   └── middleware/
│       ├── rate_limit.py # 限流中间件
│       └── logging.py    # 日志中间件
├── requirements.txt
├── Dockerfile
└── README.md
```

## 端口

- 服务端口: **8080**

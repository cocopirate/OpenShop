# App BFF (Backend For Frontend)

面向移动端 App 和微信小程序的 BFF 服务，聚合多个领域服务接口，提供适配移动端的响应格式。

## 技术选型

- **框架**: FastAPI (Python 3.11+)
- **HTTP 客户端**: httpx (异步)
- **缓存**: Redis (aioredis)

## 职责

- 接口聚合：将多个下游服务的数据合并为一次响应
- 数据裁剪：按移动端需求精简响应字段
- 缓存加速：对热点数据做 Redis 缓存
- 格式适配：统一返回格式 `{code, message, data}`

## 主要聚合接口

| 接口 | 聚合来源 |
|------|---------|
| `GET /app/v1/home` | product-service + promotion-service |
| `GET /app/v1/orders/{id}` | order-service + product-service |
| `POST /app/v1/checkout` | order-orchestration |
| `GET /app/v1/profile` | user-service + merchant-service |

## 端口

- 服务端口: **8090**

# API Gateway

统一入口网关，基于 FastAPI 实现，负责路由转发、JWT 鉴权、限流与熔断，以及可配置的请求验签与 AES+RSA 加解密。

## 技术选型

- **框架**: FastAPI (Python 3.11+)
- **鉴权**: JWT (python-jose)
- **限流**: slowapi
- **反向代理**: httpx (异步 HTTP 客户端)
- **加解密**: cryptography (AES-256-CBC, RSA-OAEP, HMAC-SHA256)

## 职责

- 统一入口：所有客户端（App、Web、小程序）流量经此进入
- JWT 校验：验证 Access Token，拒绝未授权请求
- 路由转发：将请求代理到对应的下游服务
- 限流熔断：保护后端服务免受流量冲击
- 请求日志：记录所有入站请求
- **请求验签**：对指定接口校验 HMAC-SHA256 签名（`X-Timestamp` + `X-Sign` 请求头）
- **请求解密**：对指定接口解密 AES+RSA 混合加密的请求体
- **响应加密**：对指定接口用 AES 会话密钥加密上游响应体

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
| `/api/v1/sms/**` | sms-service:8010 |

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
│   │   ├── auth.py       # JWT 鉴权中间件
│   │   └── crypto.py     # AES/RSA/HMAC 加解密工具
│   └── middleware/
│       ├── crypto_middleware.py  # 验签 / 请求解密 / 响应加密中间件
│       ├── rate_limit.py         # 限流中间件
│       └── logging.py            # 日志中间件
├── tests/
│   ├── test_auth_middleware.py
│   └── test_crypto_middleware.py
├── requirements.txt
├── Dockerfile
└── README.md
```

## 加密配置

通过 `.env` 文件中的以下变量配置加密功能（均为可选，留空则关闭对应功能）：

```dotenv
# 服务端 RSA 私钥（PEM，用于解密客户端发来的 AES 会话密钥）
CRYPTO_RSA_PRIVATE_KEY=

# HMAC-SHA256 签名密钥
CRYPTO_HMAC_SECRET=change-this-hmac-secret-in-production
```

哪些接口需要验签或加解密，通过**路由 tag** 在代码中声明（而非环境变量路径列表）：

| Tag | 功能 |
|-----|------|
| `require-sign` | 验证 `X-Timestamp` + `X-Sign` HMAC-SHA256 签名 |
| `require-encrypt-request` | 解密 AES+RSA 混合加密的请求体 |
| `require-encrypt-response` | 用 AES 会话密钥加密上游响应体 |

```python
@router.post("/api/v1/orders", tags=["require-sign", "require-encrypt-request",
                                     "require-encrypt-response"])
async def create_order(request: Request):
    ...
```

详细协议说明见 [API.md](API.md#安全加密说明)。

## 端口

- 服务端口: **8080**

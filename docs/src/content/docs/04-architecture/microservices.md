---
title: 微服务设计
---

## 设计原则

1. **单一职责**：每个服务只负责一个业务域
2. **Database per Service**：每个服务拥有独立的 PostgreSQL Schema，禁止跨服务直连数据库
3. **接口契约**：服务间通过 HTTP API 或 RabbitMQ 事件通信，定义清晰的接口契约
4. **独立部署**：每个服务可独立构建、测试、部署
5. **弹性设计**：每个服务需实现健康检查端点 `/health`

## 服务清单

| 服务 | 端口 | 职责 |
|------|------|------|
| api-gateway | 8080 | 统一入口，JWT 鉴权、限流、路由 |
| app-bff | 8090 | 面向 App/小程序 的聚合层 |
| admin-bff | 8091 | 面向管理后台的聚合层 |
| order-orchestration | 8100 | 订单流程 Saga 编排 |
| auth-service | 8000 | 统一认证、登录与 JWT 颁发 |
| admin-service | 8012 | 管理员账号、角色权限（RBAC） |
| consumer-service | 8001 | 消费者注册/登录与资料 |
| merchant-service | 8002 | 商家入驻、店铺管理 |
| product-service | 8003 | 商品 SPU/SKU 管理 |
| inventory-service | 8004 | 库存锁定/释放/扣减 |
| order-service | 8005 | 订单 CRUD，状态流转 |
| aftersale-service | 8006 | 售后申请审核 |
| promotion-service | 8007 | 优惠券、促销活动管理 |
| location-service | 8008 | 地址库，第三方地图 API |
| notification-service | 8009 | 通知业务逻辑编排 |
| sms-service | 8010 | 短信能力，多供应商 |
| virtual-number-service | 8011 | 隐私号绑定/解绑 |

## 服务目录结构（以 consumer-service 为例）

```
services/consumer-service/
├── app/
│   ├── main.py          # FastAPI 应用入口
│   ├── config.py        # pydantic-settings 配置
│   ├── models/          # SQLAlchemy ORM 模型
│   ├── schemas/         # Pydantic 请求/响应模型
│   ├── routers/         # FastAPI 路由
│   ├── services/        # 业务逻辑层
│   ├── repositories/    # 数据访问层
│   └── events/          # RabbitMQ 事件发布/消费
├── tests/
│   ├── unit/
│   └── integration/
├── alembic/             # 数据库迁移
├── requirements.txt
└── Dockerfile
```

## 共享库

位于 `libs/` 目录：

| 库 | 说明 |
|----|------|
| `common` | 公共工具，统一响应格式，异常处理 |
| `utils` | 通用工具函数 |
| `dto` | 跨服务共享的数据传输对象 |
| `event-schema` | RabbitMQ 事件 Schema 定义 |

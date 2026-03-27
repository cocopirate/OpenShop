# 项目介绍

## 什么是 OpenShop？

OpenShop 是一个基于 **FastAPI + Python** 构建的微服务电商平台，部署在 Kubernetes 上，使用云托管的 PostgreSQL 与 Redis。平台面向中大型电商业务，支持多商家入驻、订单全链路管理、通知推送、隐私号保护等核心能力。

## 核心特性

- **微服务架构**：12 个领域服务独立部署，职责清晰，可按需扩缩容
- **Saga 分布式事务**：订单创建使用 Saga 编排模式，保证跨服务数据一致性
- **事件驱动**：通过 RabbitMQ 实现服务间异步解耦
- **RBAC 权限控制**：管理后台支持细粒度的角色与权限管理
- **高性能鉴权**：JWT 无状态 + Redis 热缓存，鉴权不走数据库
- **可观测性**：结构化日志、Prometheus 指标、请求链路追踪

## 服务列表

| 服务 | 端口 | 说明 |
|------|------|------|
| api-gateway | 8080 | 统一入口，JWT 鉴权、限流 |
| app-bff | 8090 | 面向 App/小程序的 BFF |
| admin-bff | 8091 | 面向运营后台的 BFF |
| order-orchestration | 8100 | 订单流程编排（Saga） |
| user-service | 8001 | 用户与管理员管理，RBAC |
| merchant-service | 8002 | 商家入驻与管理 |
| product-service | 8003 | 商品与 SKU 管理 |
| inventory-service | 8004 | 库存管理 |
| order-service | 8005 | 订单管理 |
| aftersale-service | 8006 | 售后管理 |
| promotion-service | 8007 | 促销与优惠券管理 |
| location-service | 8008 | 地址与地图服务 |
| notification-service | 8009 | 通知服务 |
| sms-service | 8010 | 短信能力服务 |
| virtual-number-service | 8011 | 隐私号能力服务 |

## 技术栈

| 组件 | 技术选型 |
|------|---------|
| 服务框架 | FastAPI (Python 3.11+) |
| 数据库 | PostgreSQL（云托管，asyncpg） |
| 缓存 | Redis（云托管） |
| 消息队列 | RabbitMQ 3.13 |
| 搜索引擎 | Elasticsearch 8 |
| 容器编排 | Kubernetes + Kustomize |
| IaC | Terraform |
| ORM | SQLAlchemy 2.0（async） |
| 数据校验 | Pydantic v2 |
| 日志 | structlog（结构化 JSON） |
| 测试 | pytest + pytest-asyncio |
| 包管理 | uv |

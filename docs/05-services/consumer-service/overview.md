# 消费者服务（consumer-service）

## 概述

consumer-service（:8001）是 OpenShop 的 C 端用户域服务，负责：

- 消费者账号注册与资料维护
- 消费者基础身份数据管理
- 发布消费者生命周期事件（如 `customer.registered`）

说明：管理员账号、角色权限（RBAC）和鉴权令牌颁发能力已拆分至 `admin-service` 与 `auth-service`。

## 端口

| 环境 | 端口 |
|------|------|
| 本地开发 | 8001 |
| Kubernetes | `consumer-service.openshop.svc.cluster.local:8001` |

## 依赖

| 依赖 | 用途 |
|------|------|
| PostgreSQL | 消费者主数据持久化 |
| RabbitMQ | 发布消费者域事件 |

## API Swagger UI

本地开发：http://localhost:8001/docs

## 相关文档

- [API 参考](api.md)
- [数据模型](schema.md)
- [事件](events.md)

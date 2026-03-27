---
title: 订单服务
---

## 概述

order-service（:8005）负责订单的 CRUD 与状态管理：

- 创建订单（由 order-orchestration 调用）
- 订单状态流转
- 发货管理
- 发布订单相关事件（order.created / order.paid / order.shipped / order.cancelled / order.completed）

> **注意**：客户提交结账请由 order-orchestration 服务处理，order-service 只负责订单实体的持久化和状态管理。

## 端口

| 环境 | 地址 |
|------|------|
| 本地开发 | http://localhost:8005 |
| Kubernetes | `order-service.openshop.svc.cluster.local:8005` |

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/orders` | 创建订单（内部调用） |
| GET | `/api/v1/orders/{id}` | 获取订单详情 |
| GET | `/api/v1/orders` | 获取订单列表 |
| POST | `/api/v1/orders/{id}/cancel` | 取消订单 |
| POST | `/api/v1/orders/{id}/ship` | 订单发货 |

## 发布的事件

| Routing Key | 触发时机 |
|-------------|---------|
| `order.created` | 订单创建成功 |
| `order.paid` | 支付回调成功 |
| `order.shipped` | 商家发货 |
| `order.cancelled` | 订单取消 |
| `order.completed` | 客户确认收货 |

## Swagger UI

本地开发：http://localhost:8005/docs

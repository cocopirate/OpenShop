# 商家服务（merchant-service）

## 概述

merchant-service（:8002）负责商家入驻流程与店铺管理：

- 商家入驻申请与审核
- 商家信息 CRUD
- 店铺创建与管理
- 商家状态管理（pending / approved / rejected / suspended）

## 端口

| 环境 | 地址 |
|------|------|
| 本地开发 | http://localhost:8002 |
| Kubernetes | `merchant-service.openshop.svc.cluster.local:8002` |

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/merchants/apply` | 提交入驻申请 |
| GET | `/api/v1/merchants/{id}` | 获取商家详情 |
| POST | `/api/v1/admin/merchants/{id}/review` | 审核入驻申请（管理员） |
| GET | `/api/v1/admin/merchants` | 商家列表（管理员） |
| POST | `/api/v1/merchants/shops` | 创建店铺 |
| GET | `/api/v1/merchants/shops/{id}` | 获取店铺详情 |

## 依赖

- PostgreSQL：商家与店铺数据
- RabbitMQ：发布商家审核通过事件（如有）

## Swagger UI

本地开发：http://localhost:8002/docs

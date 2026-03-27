# 用户服务（user-service）

## 概述

user-service（:8001）是 OpenShop 的用户与权限管理服务，负责：

- 客户注册、登录、个人信息管理
- 管理员用户（AdminUser）CRUD
- RBAC 角色与权限管理
- JWT Token 颁发
- Redis 实时权限控制

## 端口

| 环境 | 端口 |
|------|------|
| 本地开发 | 8001 |
| Kubernetes | `user-service.openshop.svc.cluster.local:8001` |

## 依赖

| 依赖 | 用途 |
|------|------|
| PostgreSQL | 用户、角色、权限数据持久化 |
| Redis | 用户状态缓存、权限版本控制 |

## API Swagger UI

本地开发：http://localhost:8001/docs

## 相关文档

- [API 参考](api.md)
- [数据模型](schema.md)
- [事件](events.md)
- [认证 API 参考](../../03-api-reference/auth.md)
- [安全设计](../../04-architecture/security.md)

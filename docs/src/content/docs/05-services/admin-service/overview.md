---
title: 管理员服务
---

## 概述

admin-service（:8012）负责管理后台主体数据与 RBAC 能力：

- 管理员账号管理（admins）
- 角色管理（roles）
- 权限管理（permissions）
- 管理员-角色、角色-权限关联维护
- 权限/状态变更后刷新 Redis 权限缓存版本

说明：管理员登录、登出与 JWT 颁发由 auth-service 负责。

## 端口

| 环境 | 端口 |
|------|------|
| 本地开发 | 8012 |
| Kubernetes | `admin-service.openshop.svc.cluster.local:8012` |

## API Swagger UI

本地开发：http://localhost:8012/docs

## 相关文档

- [API 参考](api.md)
- [数据模型](schema.md)
- [管理员接口参考](../../03-api-reference/users.md)
- [权限设计](rbac)

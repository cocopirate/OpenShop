# 认证服务（auth-service）

## 概述

auth-service（:8000）负责统一认证与令牌能力：

- 管理员登录（`/api/auth/admin/login`）
- 消费者登录（`/api/auth/consumer/login`）
- 商家/子账号/员工登录
- 登出与 Token 失效控制（版本号机制）
- 消费者认证凭证注册

说明：管理员、角色、权限主数据由 admin-service 提供，auth-service 调用其内部接口聚合权限后签发 JWT。

## 端口

| 环境 | 端口 |
|------|------|
| 本地开发 | 8000 |
| Kubernetes | `auth-service.openshop.svc.cluster.local:8000` |

## API Swagger UI

本地开发：http://localhost:8000/docs

## 相关文档

- [API 参考](api.md)
- [认证接口参考](../../03-api-reference/auth.md)

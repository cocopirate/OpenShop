---
title: 认证服务 API
---

## 登录与登出

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/admin/login` | 管理员登录 |
| POST | `/api/auth/consumer/login` | 消费者登录 |
| POST | `/api/auth/merchant/login` | 商家主账号登录 |
| POST | `/api/auth/merchant-sub/login` | 商家子账号登录 |
| POST | `/api/auth/staff/login` | 员工登录 |
| POST | `/api/auth/logout` | 登出并使当前 Token 失效 |

## 认证凭证注册

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register/consumer` | 注册消费者认证凭证 |

## 说明

- JWT 由 auth-service 统一签发。
- API Gateway 负责验签、状态校验与权限校验。

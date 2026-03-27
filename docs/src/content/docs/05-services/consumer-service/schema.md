---
title: 消费者服务数据模型
---

## customers（消费者）

| 字段 | 类型 | 说明 |
|------|------|------|
| customer_id | UUID | 主键 |
| phone | VARCHAR(20) | UNIQUE，手机号 |
| email | VARCHAR(128) | 可选 |
| nickname | VARCHAR(64) | 昵称 |
| avatar_url | TEXT | 头像 URL |
| status | ENUM('active','disabled') | 账号状态 |
| created_at | TIMESTAMP | 注册时间 |
| updated_at | TIMESTAMP | 最后更新时间 |

## 说明

- `admin_users`、`roles`、`permissions` 等管理后台 RBAC 表已迁移至 `admin-service`。
- 登录凭证与令牌颁发逻辑已迁移至 `auth-service`。

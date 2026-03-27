# 用户服务数据模型

## admin_users（管理员用户）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigInteger | PK, 自增 | 管理员用户 ID |
| username | VARCHAR(64) | UNIQUE, NOT NULL | 登录用户名 |
| hashed_password | VARCHAR(256) | NOT NULL | bcrypt 哈希密码 |
| status | ENUM('active','disabled') | DEFAULT 'active' | 账号状态 |
| created_at | TIMESTAMP | DEFAULT now() | 创建时间 |

## roles（角色）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigInteger | PK, 自增 | 角色 ID |
| name | VARCHAR(64) | UNIQUE, NOT NULL | 角色名称 |
| desc | TEXT | | 角色描述 |
| created_at | TIMESTAMP | DEFAULT now() | 创建时间 |

## permissions（权限）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigInteger | PK, 自增 | 权限 ID |
| code | VARCHAR(128) | UNIQUE, NOT NULL | 权限码，如 `user:create` |
| name | VARCHAR(64) | NOT NULL | 权限名称 |
| type | ENUM('menu','api') | NOT NULL | 权限类型 |
| method | VARCHAR(16) | | HTTP 方法（api 类型时必填） |
| path | VARCHAR(256) | | 路由路径（api 类型时必填） |
| parent_id | BigInteger | FK → permissions.id | 父权限（树形结构） |
| created_at | TIMESTAMP | DEFAULT now() | 创建时间 |

## admin_user_roles（用户-角色关联）

| 字段 | 类型 | 说明 |
|------|------|------|
| admin_user_id | BigInteger FK | 管理员用户 ID |
| role_id | BigInteger FK | 角色 ID |

## role_permissions（角色-权限关联）

| 字段 | 类型 | 说明 |
|------|------|------|
| role_id | BigInteger FK | 角色 ID |
| permission_id | BigInteger FK | 权限 ID |

## customers（客户）

| 字段 | 类型 | 说明 |
|------|------|------|
| customer_id | UUID | PK |
| phone | VARCHAR(20) | UNIQUE，手机号 |
| email | VARCHAR(128) | 可选 |
| nickname | VARCHAR(64) | 昵称 |
| avatar_url | TEXT | 头像 URL |
| status | ENUM('active','disabled') | 账号状态 |
| created_at | TIMESTAMP | 注册时间 |

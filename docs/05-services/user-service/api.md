# 用户服务 API

## 客户接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/users/register` | 客户注册（手机号 + 验证码） |
| POST | `/api/v1/users/login` | 客户登录 |
| GET | `/api/v1/users/me` | 获取当前用户信息 |
| PUT | `/api/v1/users/me` | 更新当前用户信息 |

## 管理员接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 管理员登录，获取 JWT |
| POST | `/api/auth/logout` | 管理员登出 |
| GET | `/api/users` | 获取管理员用户列表（分页） |
| POST | `/api/users` | 创建管理员用户 |
| GET | `/api/users/{id}` | 获取管理员用户详情 |
| PUT | `/api/users/{id}` | 更新管理员用户 |
| DELETE | `/api/users/{id}` | 删除管理员用户 |
| POST | `/api/users/{id}/status` | 修改账号状态 |
| POST | `/api/users/{id}/roles` | 覆盖分配角色 |

## 角色接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/roles` | 获取角色列表 |
| POST | `/api/roles` | 创建角色 |
| GET | `/api/roles/{id}` | 获取角色详情（含权限） |
| PUT | `/api/roles/{id}` | 更新角色 |
| DELETE | `/api/roles/{id}` | 删除角色 |
| POST | `/api/roles/{id}/permissions` | 覆盖分配权限 |

## 权限接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/permissions` | 获取权限列表（树形/平铺） |
| POST | `/api/permissions` | 创建权限 |
| GET | `/api/permissions/{id}` | 获取权限详情 |
| PUT | `/api/permissions/{id}` | 更新权限 |
| DELETE | `/api/permissions/{id}` | 删除权限 |

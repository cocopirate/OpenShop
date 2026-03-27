# 管理员服务 API

## 管理员账号

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/admins` | 获取管理员列表 |
| POST | `/api/admins` | 创建管理员 |
| GET | `/api/admins/{id}` | 获取管理员详情 |
| PUT | `/api/admins/{id}` | 更新管理员 |
| DELETE | `/api/admins/{id}` | 删除管理员 |
| POST | `/api/admins/{id}/status` | 启用/禁用管理员 |
| POST | `/api/admins/{id}/roles` | 覆盖分配角色 |

## 角色管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/roles` | 获取角色列表 |
| POST | `/api/roles` | 创建角色 |
| GET | `/api/roles/{id}` | 获取角色详情 |
| PUT | `/api/roles/{id}` | 更新角色 |
| DELETE | `/api/roles/{id}` | 删除角色 |
| POST | `/api/roles/{id}/permissions` | 覆盖分配权限 |

## 权限管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/permissions` | 获取权限列表 |
| POST | `/api/permissions` | 创建权限 |
| GET | `/api/permissions/{id}` | 获取权限详情 |
| PUT | `/api/permissions/{id}` | 更新权限 |
| DELETE | `/api/permissions/{id}` | 删除权限 |

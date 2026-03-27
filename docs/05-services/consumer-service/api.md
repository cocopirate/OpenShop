# 消费者服务 API

## 消费者接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/users/register` | 消费者注册（手机号 + 验证码） |
| POST | `/api/v1/users/login` | 消费者登录 |
| GET | `/api/v1/users/me` | 获取当前消费者信息 |
| PUT | `/api/v1/users/me` | 更新当前消费者信息 |

## 边界说明

- 管理员登录、登出与 Token 颁发：`auth-service`
- 管理员用户、角色、权限管理：`admin-service`

# user-service（用户服务）

负责用户注册、登录、个人信息管理及用户画像维护。

## 职责

- 用户注册与登录（手机号/邮箱）
- JWT Token 颁发与刷新
- 个人信息维护与隐私保护

## 主要接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `POST /api/v1/users` | POST | 创建用户 |
| `GET /api/v1/users/{user_id}` | GET | 获取用户信息 |
| `PUT /api/v1/users/{user_id}` | PUT | 更新用户信息 |
| `GET /api/v1/users/{user_id}/profile` | GET | 获取用户画像 |

## 数据模型

- User
- UserProfile
- UserAddress

## 依赖服务

- sms-service（发送验证码）
- notification-service（账户变更通知）

## 端口

- 服务端口: **8001**

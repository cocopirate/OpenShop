# 用户服务事件

## 发布的事件

| Routing Key | 触发时机 | 消费者 |
|-------------|---------|--------|
| `customer.registered` | 客户注册成功 | notification-service |

## 事件 Schema

### customer.registered

```python
class CustomerRegisteredEvent(BaseModel):
    customer_id: str
    phone_masked: str       # 脱敏手机号，如 138****8000
    nickname: str
    registered_at: datetime
```

## 消费的事件

user-service 当前不消费其他服务的事件。

## Redis 实时控制

user-service 在以下操作时主动更新 Redis，供 API Gateway 实时鉴权使用：

| 操作 | Redis 更新 |
|------|-----------|
| 禁用账号 | `SET user_status:{uid} "disabled"` |
| 启用账号 | `SET user_status:{uid} "active"` |
| 修改角色/权限 | `INCR user_perm_ver:{uid}`，`DEL user_permissions:{uid}` |

# 消费者服务事件

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

consumer-service 当前不消费其他服务的事件。

## 说明

Redis 中与管理员权限版本、用户状态相关的键更新职责已迁移到 `admin-service` 和 `auth-service`。

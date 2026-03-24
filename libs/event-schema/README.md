# Libs - Event Schema

## 职责

定义跨服务的事件契约，所有发布/订阅的消息体均在此声明，防止各服务各自定义导致不一致。

## 事件列表

| 事件名 | 发布方 | 消费方 | 说明 |
|--------|--------|--------|------|
| `order.created` | order-service | inventory-service, communication-service | 订单创建 |
| `order.cancelled` | order-service | inventory-service | 订单取消，库存回滚 |
| `inventory.low` | inventory-service | communication-service | 库存不足告警 |
| `user.registered` | user-service | communication-service | 新用户注册欢迎通知 |
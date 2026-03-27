# 事件驱动架构

## RabbitMQ 路由键一览

| Routing Key | 生产者 | 消费者 | 说明 |
|-------------|--------|--------|------|
| `order.created` | order-service | inventory-service, notification-service | 订单创建 |
| `order.paid` | order-service | inventory-service, promotion-service, notification-service | 订单支付成功 |
| `order.cancelled` | order-service | inventory-service, notification-service | 订单取消 |
| `order.shipped` | order-service | notification-service, virtual-number-service | 订单发货 |
| `order.completed` | order-service | promotion-service | 订单完成 |
| `inventory.locked` | inventory-service | order-orchestration | 库存锁定确认 |
| `inventory.lock_failed` | inventory-service | order-orchestration | 库存锁定失败 |
| `customer.registered` | consumer-service | notification-service | 客户注册 |
| `aftersale.approved` | aftersale-service | notification-service, order-service | 售后审核通过 |

## 设计原则

1. **至少一次投递（At-Least-Once）**：消息可能重复投递，消费者需实现幂等处理
2. **事件 Schema 版本化**：通过 `libs/event-schema` 统一管理事件结构
3. **Dead Letter Queue**：消费失败的消息进入死信队列，便于排查

## 事件 Schema 示例

```python
# libs/event-schema/order_events.py
from pydantic import BaseModel
from datetime import datetime

class OrderCreatedEvent(BaseModel):
    order_id: str
    customer_id: str
    total_amount: str
    items: list[dict]
    created_at: datetime
```

## 消费者幂等处理

消费者在处理消息前，通过业务主键（如 `order_id`）判断是否已处理：

```python
async def handle_order_created(event: OrderCreatedEvent):
    if await repository.exists(event.order_id):
        return  # 已处理，幂等跳过
    await repository.process(event)
```

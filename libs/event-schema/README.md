# event-schema（RabbitMQ 事件 Schema 库）

定义服务间通过 RabbitMQ 传递的事件消息结构，使用 Pydantic v2 进行校验。

## 事件定义

- **order_events.py**：订单事件（OrderCreatedEvent, OrderPaidEvent, OrderCancelledEvent, OrderShippedEvent）
- **inventory_events.py**：库存事件（InventoryLockedEvent, InventoryLockFailedEvent）
- **user_events.py**：用户事件（UserRegisteredEvent）
- **aftersale_events.py**：售后事件（AftersaleApprovedEvent）

## 使用方式

```python
import aio_pika
from libs.event_schema.order_events import OrderCreatedEvent

# 生产者
connection = await aio_pika.connect_robust("amqp://guest:guest@localhost:5672/")
async with connection:
    channel = await connection.channel()
    exchange = await channel.declare_exchange("openshop", aio_pika.ExchangeType.TOPIC)
    event = OrderCreatedEvent(order_id="ORD-001", user_id="USR-001", total=99.0)
    await exchange.publish(
        aio_pika.Message(body=event.model_dump_json().encode()),
        routing_key="order.created",
    )

# 消费者
event = OrderCreatedEvent.model_validate_json(message.body)
```

## 技术依赖

- Python 3.11+
- Pydantic v2
- aio-pika

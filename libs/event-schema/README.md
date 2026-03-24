# event-schema（Kafka 事件 Schema 库）

定义服务间通过 Kafka 传递的事件消息结构，使用 Pydantic v2 进行校验。

## 事件定义

- **order_events.py**：订单事件（OrderCreatedEvent, OrderPaidEvent, OrderCancelledEvent, OrderShippedEvent）
- **inventory_events.py**：库存事件（InventoryLockedEvent, InventoryLockFailedEvent）
- **user_events.py**：用户事件（UserRegisteredEvent）
- **aftersale_events.py**：售后事件（AftersaleApprovedEvent）

## 使用方式

```python
from libs.event_schema.order_events import OrderCreatedEvent

# 生产者
event = OrderCreatedEvent(order_id="ORD-001", user_id="USR-001", total=99.0)
await producer.send("order.created", event.model_dump_json().encode())

# 消费者
event = OrderCreatedEvent.model_validate_json(message.value)
```

## 技术依赖

- Python 3.11+
- Pydantic v2
- aiokafka

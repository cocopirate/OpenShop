# 幂等性设计

## 什么是幂等性？

幂等性指同一操作执行多次与执行一次的效果相同。在分布式系统中，网络超时、重试、消息重复投递都可能导致操作被执行多次，幂等性设计可以防止数据重复创建或状态异常。

## request_id 幂等方案

OpenShop 全链路使用 `request_id`（UUID）保证写操作幂等：

1. **客户端**：每次发起写操作时生成唯一 UUID 作为 `request_id`
2. **服务端**：收到请求后，先检查 Redis 中是否存在该 `request_id`
   - 存在：直接返回首次处理结果
   - 不存在：执行业务逻辑，将结果存入 Redis（TTL 24h）

```python
async def create_order(request: OrderRequest, redis: Redis):
    cache_key = f"idempotency:{request.request_id}"

    # 检查幂等键
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # 执行业务逻辑
    order = await order_service.create(request)

    # 存储结果（TTL 24小时）
    await redis.setex(cache_key, 86400, order.json())
    return order
```

## 数据库层幂等

对于需要持久化的幂等控制，使用数据库唯一键：

```sql
-- 短信发送记录以 request_id 为唯一键
ALTER TABLE sms_records ADD CONSTRAINT uq_request_id UNIQUE (request_id);
```

服务端捕获 `UniqueViolationError` 并返回已有记录，而非报错。

## 消息消费幂等

RabbitMQ 消费者在处理消息前检查是否已处理：

```python
async def handle_order_created(event: OrderCreatedEvent):
    # 以业务主键判断幂等
    if await inventory_repo.is_locked(event.order_id):
        logger.info("already_processed", order_id=event.order_id)
        return
    await inventory_repo.lock(event.order_id, event.items)
```

## 幂等 TTL 选择

| 场景 | TTL | 说明 |
|------|-----|------|
| API 请求幂等 | 24 小时 | 客户端重试窗口 |
| 短信验证码 | 5 分钟 | 验证码有效期 |
| 事件消费 | 基于业务状态 | 通过数据库主键判断 |

# 重试策略

## 何时重试？

以下情况适合重试：

- 网络超时（`httpx.TimeoutException`）
- 服务暂时不可用（5xx 错误）
- 数据库连接失败（临时故障）

以下情况**不应**重试：

- 业务错误（4xx，如参数校验失败、资源不存在）
- 幂等性未保证的操作（避免重复写入）

## HTTP 客户端重试

使用指数退避（Exponential Backoff）+ 抖动（Jitter）：

```python
import asyncio
import random

async def http_request_with_retry(
    client: httpx.AsyncClient,
    url: str,
    payload: dict,
    max_retries: int = 3,
) -> dict:
    for attempt in range(max_retries):
        try:
            resp = await client.post(url, json=payload, timeout=5.0)
            resp.raise_for_status()
            return resp.json()
        except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
            if attempt == max_retries - 1:
                raise
            # 指数退避 + 随机抖动：1s, 2s, 4s ...（±0.5s）
            wait = (2 ** attempt) + random.uniform(-0.5, 0.5)
            await asyncio.sleep(wait)
```

## 熔断器模式

sms-service 内置熔断器，防止故障级联：

```
正常状态（Closed）
    │ 连续失败 N 次
    ▼
熔断状态（Open）——等待恢复超时——→ 半开状态（Half-Open）
    │ 继续失败                          │ 成功
    └────────────────────────────────────┘ 恢复到 Closed
```

配置：

```bash
SMS_PROVIDER_FAILURE_THRESHOLD=3      # 连续失败 3 次触发熔断
SMS_PROVIDER_RECOVERY_TIMEOUT=60      # 60 秒后进入半开状态
```

## RabbitMQ 消息重试

消费者处理失败时，消息会被重新入队（`nack + requeue=True`）。建议配合 **Dead Letter Queue（DLQ）** 处理多次重试后仍失败的消息：

```python
async def handle_message(message: AbstractIncomingMessage):
    try:
        await process(message)
        await message.ack()
    except Exception as e:
        logger.error("message_processing_failed", error=str(e))
        # 重试次数超过阈值时放入死信队列
        if message.headers.get("x-death-count", 0) >= 3:
            await message.reject(requeue=False)  # 进入 DLQ
        else:
            await message.nack(requeue=True)
```

## 重试注意事项

1. **保证幂等**：重试的操作必须是幂等的（携带 `request_id`）
2. **设置上限**：重试次数不超过 3–5 次，避免无限循环
3. **记录日志**：每次重试都记录日志，便于排查问题
4. **告警**：重试次数达到上限时触发告警

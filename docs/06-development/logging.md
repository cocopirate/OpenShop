# 日志规范

## 技术选型

使用 **structlog** 进行结构化日志输出，所有日志以 JSON 格式写入 stdout，便于日志聚合系统（如 ELK、Loki）解析。

## 初始化配置

```python
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()
```

## 日志级别规范

| 级别 | 使用场景 |
|------|---------|
| DEBUG | 开发调试信息，生产环境不输出 |
| INFO | 正常业务事件（请求接收、订单创建等） |
| WARNING | 可恢复的异常（重试、降级） |
| ERROR | 需要关注的错误（外部服务失败、数据库异常） |
| CRITICAL | 服务不可用级别的严重错误 |

## 结构化日志格式

```python
logger.info(
    "order_created",
    order_id=order.order_id,
    customer_id=order.customer_id,
    total_amount=str(order.total_amount),
    request_id=request_id,
)
```

输出：
```json
{
  "event": "order_created",
  "order_id": "uuid",
  "customer_id": "uuid",
  "total_amount": "168.00",
  "request_id": "uuid",
  "level": "info",
  "timestamp": "2024-01-01T00:00:00Z",
  "logger": "order_service.routers.order"
}
```

## 必须包含的字段

每条日志必须包含：

- `request_id`：请求链路 ID，从 Header 或生成
- `service`：服务名称（通过 structlog bound logger 绑定）

## 敏感信息脱敏

- 手机号：`13800138000` → `138****8000`
- 密码：禁止出现在任何日志中
- API Key：禁止出现在任何日志中

```python
def mask_phone(phone: str) -> str:
    return phone[:3] + "****" + phone[-4:]
```

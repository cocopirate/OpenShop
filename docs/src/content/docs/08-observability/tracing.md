---
title: 链路追踪
---

## 当前方案：Request ID 传播

目前通过 `request_id` 实现轻量级链路追踪：

1. API Gateway 为每个请求生成 UUID 作为 `request_id`
2. 通过 `X-Request-ID` HTTP Header 透传到所有下游服务
3. 所有服务日志中记录 `request_id`
4. 通过日志聚合系统（如 Kibana）按 `request_id` 过滤，还原完整调用链

## 查询链路日志

在 Kibana 或 Grafana Loki 中，通过 `request_id` 过滤：

```
request_id:"550e8400-e29b-41d4-a716-446655440000"
```

## 进阶：OpenTelemetry（规划中）

建议后续接入 OpenTelemetry，实现完整的分布式追踪：

```
OpenTelemetry SDK（各服务）
    │
    ▼
OTLP Exporter
    │
    ▼
OpenTelemetry Collector
    │
    ▼
Jaeger / Tempo（追踪后端）
    │
    ▼
Grafana（可视化）
```

**接入步骤（以 FastAPI 为例）：**

```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

FastAPIInstrumentor.instrument_app(app)
```

## 关键链路

需要重点关注的跨服务调用链路：

1. **下单链路**：client → app-bff → api-gateway → order-orchestration → promotion-service / inventory-service / order-service
2. **短信通知链路**：notification-service → sms-service → 供应商
3. **售后链路**：client → api-gateway → aftersale-service → notification-service / order-service

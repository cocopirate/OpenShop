# 日志

## 日志架构

```
各微服务（structlog → JSON stdout）
    │
    ▼
容器日志驱动（Docker / Kubernetes）
    │
    ▼
日志聚合（Fluentd / Filebeat）
    │
    ▼
Elasticsearch / Loki
    │
    ▼
Kibana / Grafana 可视化
```

## 日志格式

所有服务输出 JSON 格式结构化日志：

```json
{
  "event": "order_created",
  "order_id": "uuid",
  "customer_id": "uuid",
  "total_amount": "168.00",
  "request_id": "uuid",
  "service": "order-service",
  "level": "info",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 请求链路追踪

API Gateway 为每个请求生成唯一 `request_id`（UUID），并通过 Header `X-Request-ID` 透传到所有下游服务。所有日志记录时必须包含 `request_id`，便于跨服务链路追踪。

## 日志级别配置

通过环境变量控制：

```bash
LOG_LEVEL=INFO   # 生产环境
LOG_LEVEL=DEBUG  # 开发环境
```

## 查看 Kubernetes 日志

```bash
# 实时查看 consumer-service 日志
kubectl logs -f deployment/consumer-service -n openshop

# 查看最近 100 行
kubectl logs --tail=100 deployment/order-service -n openshop

# 查看某个 Pod 的日志
kubectl logs consumer-service-6d4b9f5-xyz -n openshop
```

## 敏感信息脱敏规则

| 字段 | 脱敏方式 |
|------|---------|
| 手机号 | `13800138000` → `138****8000` |
| 邮箱 | `user@example.com` → `u***@example.com` |
| 密码 | 永远不输出 |
| API Key | 永远不输出 |

---
title: 指标监控
---

## 当前方案

各服务通过 FastAPI + Prometheus 客户端暴露指标端点：

```
GET /metrics
```

## sms-service 已有指标

| 指标名 | 类型 | 说明 | 标签 |
|--------|------|------|------|
| `sms_send_total` | Counter | 短信发送总次数 | `provider`, `status` |
| `sms_send_latency_seconds` | Histogram | 短信发送延迟 | `provider` |

## 建议的通用指标

每个服务建议暴露以下通用指标：

| 指标名 | 类型 | 说明 |
|--------|------|------|
| `http_requests_total` | Counter | HTTP 请求总数，按 method/path/status_code |
| `http_request_duration_seconds` | Histogram | HTTP 请求延迟 |
| `db_query_duration_seconds` | Histogram | 数据库查询延迟 |

## Prometheus 配置（示例）

```yaml
scrape_configs:
  - job_name: 'openshop-services'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: "true"
```

## Grafana 看板

建议创建以下看板：

1. **服务总览**：请求量、错误率、P99 延迟
2. **短信服务**：发送成功率、供应商切换、熔断状态
3. **订单漏斗**：下单 → 支付 → 发货 → 完成各阶段转化率
4. **基础设施**：PostgreSQL 连接池、Redis 命中率、RabbitMQ 队列深度

## 告警规则示例

```yaml
# 错误率告警
- alert: HighErrorRate
  expr: rate(http_requests_total{status_code=~"5.."}[5m]) > 0.05
  for: 5m
  annotations:
    summary: "服务 {{ $labels.service }} 错误率超过 5%"

# 短信发送失败告警
- alert: SmsFailureRate
  expr: rate(sms_send_total{status="failed"}[5m]) > 0.1
  for: 2m
  annotations:
    summary: "短信发送失败率过高"
```

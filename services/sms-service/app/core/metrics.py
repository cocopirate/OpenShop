"""Prometheus metrics for sms-service."""
from prometheus_client import Counter, Gauge, Histogram

sms_send_total = Counter(
    "sms_send_total",
    "Total number of SMS send attempts",
    ["provider", "status"],
)

sms_send_latency = Histogram(
    "sms_send_latency_seconds",
    "SMS send latency in seconds",
    ["provider"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0],
)

sms_rate_limit_triggered_total = Counter(
    "sms_rate_limit_triggered_total",
    "Total number of rate limit triggers",
    ["dimension"],  # "phone" or "ip"
)

sms_provider_success_rate = Gauge(
    "sms_provider_success_rate",
    "Rolling success rate of SMS provider (last 100 sends)",
    ["provider"],
)

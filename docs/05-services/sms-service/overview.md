# 短信服务（sms-service）

## 概述

sms-service（:8010）是短信发送能力服务，与业务无关，提供：

- 多供应商支持（阿里云、腾讯云、创蓝）
- 熔断器（Circuit Breaker）：主供应商故障时自动切换备用
- 限流：按手机号（1次/分钟，10次/天）和 IP（10次/分钟）限速
- 幂等性：通过 `request_id` + Redis 去重（TTL 24h）
- 短信模板管理
- 发送记录存储与查询
- 运行时配置动态更新

## 端口

| 环境 | 地址 |
|------|------|
| 本地开发 | http://localhost:8010 |
| Kubernetes | `sms-service.openshop.svc.cluster.local:8010` |

## 关键环境变量

```bash
SMS_PROVIDER=aliyun                   # 主供应商
SMS_PROVIDER_FALLBACK=tencent         # 备用供应商
SMS_PROVIDER_FAILURE_THRESHOLD=3      # 连续失败 N 次触发熔断
SMS_PROVIDER_RECOVERY_TIMEOUT=60      # 熔断恢复等待时间（秒）
SMS_CODE_TTL=300                      # 验证码有效期（秒）
SMS_RECORDS_RETENTION_DAYS=90         # 发送记录保留天数
```

## Prometheus 指标

| 指标名 | 类型 | 说明 |
|--------|------|------|
| `sms_send_total` | Counter | 短信发送总次数，按供应商和状态分组 |
| `sms_send_latency_seconds` | Histogram | 短信发送延迟 |

## API 参考

详见 [短信服务 API](../../03-api-reference/sms.md)

## Swagger UI

本地开发：http://localhost:8010/docs

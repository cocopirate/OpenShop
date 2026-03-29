---
title: 短信服务
---

## 概述

sms-service（:8010）是短信发送能力服务，与业务无关，提供：

- 多供应商支持（阿里云、腾讯云、创蓝）
- 熔断器（Circuit Breaker）：主供应商故障时自动切换备用
- 限流：按手机号（1次/分钟，10次/天）和 IP（10次/分钟）限速
- 幂等性：通过 `request_id` + Redis 去重（TTL 24h）
- 短信模板管理
- 发送记录存储与查询
- **多租户渠道路由**：为不同业务方配置独立供应商和凭据（通过管理后台 API 持久化）
- **客户端 API Key 管理**：`X-API-Key → 渠道名称` 映射，控制 `send-code` 接口的访问与路由
- 运行时配置动态更新（供应商凭据、限频参数、熔断器参数等，全部持久化到 DB）

## 端口

| 环境 | 地址 |
|------|------|
| 本地开发 | http://localhost:8010 |
| Kubernetes | `sms-service.openshop.svc.cluster.local:8010` |

## 配置管理

SMS 服务的所有运营配置（供应商凭据、限频参数、熔断器、渠道路由、客户端 Key）均通过管理后台 API 持久化到数据库，**不使用环境变量**，服务重启后自动从 `sms_config_store` 表恢复。

`.env` 只需配置基础设施连接信息：

```bash
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
```

首次部署通过 API 写入配置：

```bash
# 配置默认供应商
curl -X PUT http://localhost:8010/api/sms/config \
  -H "Content-Type: application/json" \
  -d '{"sms_provider":"aliyun_phone_svc","aliyun_phone_svc":{"access_key_id":"xxx","access_key_secret":"xxx","sign_name":"你的签名"}}'

# 创建业务渠道
curl -X PUT http://localhost:8010/api/sms/channels/business_a \
  -H "Content-Type: application/json" \
  -d '{"provider":"aliyun_phone_svc","access_key_id":"k1","access_key_secret":"s1","sign_name":"A业务"}'

# 绑定客户端 API Key
curl -X POST http://localhost:8010/api/sms/client-keys \
  -H "Content-Type: application/json" \
  -d '{"api_key":"key-a-001","channel":"business_a"}'
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

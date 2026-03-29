---
title: 短信服务
---

## 概述

sms-service（:8010）是短信发送能力服务，与业务无关，提供：

- 多供应商支持（阿里云、腾讯云、创蓝）
- 熔断器（Circuit Breaker）：主供应商故障时自动切换备用（由策略配置）
- 限流：按手机号和 IP 维度限速（限频规则由策略配置）
- 幂等性：通过 `request_id` + Redis 去重（TTL 24h）
- 短信模板管理
- 发送记录存储与查询
- **多租户渠道路由**：为不同业务方配置独立供应商和凭据（通过渠道 API 持久化到 DB）
- **策略管理**：每个渠道关联一个策略，策略控制限频、验证码 TTL、熔断器阈值和备用渠道
- **客户端 API Key 管理**：`X-API-Key → 渠道名称` 映射，控制 `send-code` 接口的访问与路由

## 端口

| 环境 | 地址 |
|------|------|
| 本地开发 | http://localhost:8010 |
| Kubernetes | `sms-service.openshop.svc.cluster.local:8010` |

## 初始化行为

服务启动时：
1. 若 `sms_policies` 表中不存在 `default` 策略 → **自动创建默认策略**（使用内置默认值）
2. 若 `sms_channels` 表为空 → **自动创建 `_default` 渠道**，关联 `default` 策略，标记为默认渠道

首次部署只需配置基础设施连接后，通过 API 写入供应商凭据即可：

```bash
# 配置默认渠道（阿里云）
curl -X PUT http://localhost:8010/api/sms/channels/_default \
  -H "Content-Type: application/json" \
  -d '{"provider":"aliyun","is_default":true,"policy_name":"default","access_key_id":"xxx","access_key_secret":"xxx","sign_name":"你的签名"}'

# 创建宽松策略（内部服务）
curl -X PUT http://localhost:8010/api/sms/policies/internal \
  -H "Content-Type: application/json" \
  -d '{"code_ttl":600,"rate_limit_phone_per_minute":5,"rate_limit_phone_per_day":50,"rate_limit_ip_per_minute":50,"rate_limit_ip_per_day":500,"failure_threshold":5,"recovery_timeout":30}'

# 创建业务渠道，绑定内部策略
curl -X PUT http://localhost:8010/api/sms/channels/business_a \
  -H "Content-Type: application/json" \
  -d '{"provider":"aliyun_phone_svc","policy_name":"internal","access_key_id":"k1","access_key_secret":"s1","sign_name":"A业务"}'

# 绑定客户端 API Key
curl -X POST http://localhost:8010/api/sms/client-keys \
  -H "Content-Type: application/json" \
  -d '{"api_key":"key-a-001","channel":"business_a"}'
```

## 配置说明

`.env` 只需配置基础设施连接信息：

```bash
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
```

所有运营配置（供应商凭据、限频参数、熔断器、渠道路由、客户端 Key）均通过 API 写入数据库，服务重启后自动恢复。

## Prometheus 指标

| 指标名 | 类型 | 说明 |
|--------|------|------|
| `sms_send_total` | Counter | 短信发送总次数，按供应商和状态分组 |
| `sms_send_latency_seconds` | Histogram | 短信发送延迟 |

## API 参考

详见 [短信服务 API](../../03-api-reference/sms.md)

## Swagger UI

本地开发：http://localhost:8010/docs

## HTTP 接口

### 短信发送

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/sms/send` | 发送短信（支持幂等 `request_id` 和渠道路由 `channel`） |
| `POST` | `/api/sms/send-code` | 发送验证码（需 `X-API-Key` 请求头，若配置了客户端 Key） |
| `POST` | `/api/sms/verify` | 校验验证码 |

### 发送记录

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/sms/records` | 查询发送记录（手机号/时间/状态过滤 + 分页） |
| `DELETE` | `/api/sms/records/{id}` | 删除指定发送记录 |

### 短信模板

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/sms/templates` | 模板列表（供应商/状态过滤 + 分页） |
| `POST` | `/api/sms/templates` | 创建模板 |
| `GET` | `/api/sms/templates/{id}` | 模板详情 |
| `PUT` | `/api/sms/templates/{id}` | 更新模板 |
| `DELETE` | `/api/sms/templates/{id}` | 删除模板 |

### 策略管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/sms/policies` | 策略列表 |
| `POST` | `/api/sms/policies` | 创建策略（自动生成名称） |
| `GET` | `/api/sms/policies/{name}` | 策略详情 |
| `PUT` | `/api/sms/policies/{name}` | 创建或替换策略 |
| `PATCH` | `/api/sms/policies/{name}` | 局部更新策略 |
| `DELETE` | `/api/sms/policies/{name}` | 删除策略（被渠道引用时返回 409） |

### 渠道管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/sms/channels` | 查询渠道列表（敏感字段已脱敏） |
| `GET` | `/api/sms/channels/{name}` | 查询单个渠道详情 |
| `PUT` | `/api/sms/channels/{name}` | 创建或全量替换渠道配置 |
| `PATCH` | `/api/sms/channels/{name}` | 局部更新渠道字段 |
| `DELETE` | `/api/sms/channels/{name}` | 删除渠道 |

### 客户端 API Key 管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/sms/client-keys` | 查询所有 `X-API-Key → 渠道名称` 映射 |
| `POST` | `/api/sms/client-keys` | 添加或覆写一条映射 |
| `DELETE` | `/api/sms/client-keys/{api_key}` | 删除指定 API Key |

### 健康检测

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 服务存活检查（含 DB/Redis 连通性） |
| `GET` | `/health/ready` | K8s Readiness Probe |

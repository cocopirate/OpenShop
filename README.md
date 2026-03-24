# OpenShop 微服务平台

一个基于微服务架构的电商平台，包含订单、库存、用户、通知、地图及隐私号等核心业务域。

## 架构总览

```
                        ┌─────────────────┐
   Client / App  ──────▶│   API Gateway   │
                        │    (BFF Layer)  │
                        └────────┬────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
   ┌──────▼──────┐     ┌─────────▼─────┐     ┌─────────▼──────┐
   │order-service│     │ user-service  │     │inventory-service│
   └──────┬──────┘     └───────────────┘     └────────────────┘
          │ Event
   ┌──────▼─────────────────────┐
   │  Message Broker (MQ)       │
   └──────┬─────────────────────┘
          │
   ┌──────▼──────────────────────────────────┐
   │ communication / map / privacy-number    │
   └─────────────────────────────────────────┘
```

## 快速启动

```bash
# 启动基础设施
docker-compose -f infra/docker-compose.yml up -d

# 检查服务状态
./scripts/health-check.sh
```

## 文档

- [架构设计](docs/architecture.md)
- [领域模型](docs/domain-model.md)
- [事件流设计](docs/event-flow.md)
- [API 契约](docs/api-contract.md)

## 服务列表

| 服务 | 端口 | 说明 |
|------|------|------|
| api-gateway | 8080 | 统一入口 |
| order-service | 8081 | 订单管理 |
| inventory-service | 8082 | 库存管理 |
| user-service | 8083 | 用户管理 |
| communication-service | 8084 | 短信/通知 |
| map-service | 8085 | 地图服务 |
| privacy-number-service | 8086 | 隐私号服务 |
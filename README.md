# OpenShop 微服务电商平台

基于 FastAPI + Python 的微服务电商平台，运行于 Kubernetes，使用云托管 PostgreSQL 与 Redis。

## 架构总览

```
┌──────────────────────────────────────────────────────────────────┐
│                          入口层 (Entry Layer)                      │
│           App-BFF (:8090)          Admin-BFF (:8091)              │
│                    API Gateway (:8080)                             │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│                     编排层 (Orchestration Layer)                    │
│                  order-orchestration (:8100)                       │
└──────┬──────┬──────┬──────┬──────┬──────┬──────┬────────────────┘
       │      │      │      │      │      │      │
┌──────▼──────────────────────────────────────────────────────────┐
│                      领域服务层 (Domain Services)                   │
│  user(:8001) merchant(:8002) product(:8003) inventory(:8004)     │
│  order(:8005) aftersale(:8006) promotion(:8007) location(:8008) │
│  notification(:8009)                                             │
└─────────────────────────────────────────────────────────────────┘
       │                           │
┌──────▼───────────────────────────▼──────────────────────────────┐
│                      能力服务层 (Capability Services)               │
│              sms-service(:8010)  virtual-number-service(:8011)  │
└─────────────────────────────────────────────────────────────────┘
       │                           │
┌──────▼───────────────────────────▼──────────────────────────────┐
│                         基础设施层                                   │
│     PostgreSQL   Redis   Kafka   Elasticsearch                   │
└─────────────────────────────────────────────────────────────────┘
```

## 快速启动

```bash
# 启动基础设施（本地开发）
docker-compose -f infra/docker-compose.yml up -d

# 检查服务健康状态
./scripts/health-check.sh

# 启动所有服务（开发模式）
./scripts/start-all.sh
```

## 服务列表

| 服务 | 端口 | 说明 |
|------|------|------|
| api-gateway | 8080 | 统一入口，JWT 鉴权、限流 |
| app-bff | 8090 | 面向 App/小程序的 BFF |
| admin-bff | 8091 | 面向运营后台的 BFF |
| order-orchestration | 8100 | 订单流程编排 |
| user-service | 8001 | 用户管理 |
| merchant-service | 8002 | 商家管理 |
| product-service | 8003 | 商品管理 |
| inventory-service | 8004 | 库存管理 |
| order-service | 8005 | 订单管理 |
| aftersale-service | 8006 | 售后管理 |
| promotion-service | 8007 | 促销管理 |
| location-service | 8008 | 地址/地图服务 |
| notification-service | 8009 | 通知服务 |
| sms-service | 8010 | 短信能力服务 |
| virtual-number-service | 8011 | 隐私号能力服务 |

## 文档

- [架构设计](docs/architecture.md)
- [领域模型](docs/domain-model.md)
- [事件流设计](docs/event-flow.md)
- [API 契约](docs/api-contract.md)

## 目录结构

```
OpenShop/
├── bff/
│   ├── api-gateway/        # 统一网关
│   ├── app-bff/            # App BFF
│   └── admin-bff/          # 管理后台 BFF
├── orchestration/
│   └── order-orchestration/ # 订单编排服务
├── services/
│   ├── user-service/
│   ├── merchant-service/
│   ├── product-service/
│   ├── inventory-service/
│   ├── order-service/
│   ├── aftersale-service/
│   ├── promotion-service/
│   ├── location-service/
│   ├── notification-service/
│   ├── sms-service/
│   └── virtual-number-service/
├── libs/
│   ├── common/             # 公共工具库
│   ├── utils/              # 通用工具函数
│   ├── dto/                # 数据传输对象
│   └── event-schema/       # 事件 Schema 定义
├── infra/
│   ├── docker-compose.yml  # 本地开发基础设施
│   ├── k8s/                # Kubernetes 配置
│   └── terraform/          # 云资源 IaC
├── docs/                   # 设计文档
└── scripts/                # 运维脚本
```

## 技术栈

| 组件 | 技术选型 |
|------|---------|
| 服务框架 | FastAPI (Python 3.11+) |
| 数据库 | PostgreSQL (云托管) |
| 缓存 | Redis (云托管) |
| 消息队列 | Kafka |
| 搜索引擎 | Elasticsearch |
| 容器编排 | Kubernetes |
| 服务发现 | Kubernetes DNS |
| 配置管理 | Kubernetes ConfigMap + Secret |
| ORM | SQLAlchemy 2.0 (async) |
| 数据校验 | Pydantic v2 |

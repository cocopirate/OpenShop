# OpenShop 微服务电商平台

> 基于 FastAPI + Python 的微服务电商平台，运行于 Kubernetes，使用云托管 PostgreSQL 与 Redis。

## 平台简介

OpenShop 是一个完整的微服务电商解决方案，采用现代化的技术栈和架构模式，支持高并发、高可用的电商业务场景。

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
│     PostgreSQL   Redis   RabbitMQ   Elasticsearch                   │
└─────────────────────────────────────────────────────────────────┘
```

## 快速开始

```bash
# 启动基础设施（本地开发）
docker-compose -f infra/docker-compose.yml up -d

# 启动所有服务（开发模式）
./scripts/start-all.sh

# 检查服务健康状态
./scripts/health-check.sh
```

## 技术栈

| 组件 | 技术选型 |
|------|---------|
| 服务框架 | FastAPI (Python 3.11+) |
| 数据库 | PostgreSQL (云托管) |
| 缓存 | Redis (云托管) |
| 消息队列 | RabbitMQ |
| 搜索引擎 | Elasticsearch |
| 容器编排 | Kubernetes |
| ORM | SQLAlchemy 2.0 (async) |
| 数据校验 | Pydantic v2 |

## 文档导航

- [项目介绍](00-overview/introduction.md)
- [快速启动](01-getting-started/quick-start.md)
- [架构设计](04-architecture/system-overview.md)
- [API 参考](03-api-reference/auth.md)
- [部署指南](07-deployment/k8s-deploy.md)

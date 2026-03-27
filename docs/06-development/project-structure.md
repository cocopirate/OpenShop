# 项目结构

## 顶层目录

```
OpenShop/
├── bff/                    # 入口层：API 网关 + BFF
│   ├── api-gateway/        # 统一 API 网关（:8080）
│   ├── app-bff/            # App/小程序 BFF（:8090）
│   └── admin-bff/          # 管理后台 BFF（:8091）
├── orchestration/
│   └── order-orchestration/ # 订单 Saga 编排（:8100）
├── services/               # 领域服务 + 能力服务
│   ├── auth-service/       # 认证与令牌（:8000）
│   ├── admin-service/      # 管理员与 RBAC（:8012）
│   ├── consumer-service/   # 消费者用户域（:8001）
│   ├── merchant-service/   # 商家管理（:8002）
│   ├── product-service/    # 商品管理（:8003）
│   ├── inventory-service/  # 库存管理（:8004）
│   ├── order-service/      # 订单管理（:8005）
│   ├── aftersale-service/  # 售后管理（:8006）
│   ├── promotion-service/  # 促销管理（:8007）
│   ├── location-service/   # 地址/地图（:8008）
│   ├── notification-service/ # 通知服务（:8009）
│   ├── sms-service/        # 短信能力（:8010）
│   └── virtual-number-service/ # 隐私号（:8011）
├── libs/                   # 共享库
│   ├── common/             # 公共工具、响应格式、异常
│   ├── utils/              # 通用工具函数
│   ├── dto/                # 跨服务 DTO
│   └── event-schema/       # RabbitMQ 事件 Schema
├── infra/
│   ├── docker-compose.yml  # 本地基础设施
│   ├── k8s/                # Kubernetes 配置（Kustomize）
│   └── terraform/          # 云资源 IaC
├── docs/                   # 本文档
├── scripts/
│   ├── start-all.sh        # 一键启动所有服务
│   └── health-check.sh     # 健康检查
└── .env.example            # 环境变量模板
```

## 单个服务目录结构

```
services/{service-name}/
├── app/
│   ├── main.py             # FastAPI 入口，注册路由和中间件
│   ├── config.py           # pydantic-settings 配置类
│   ├── models/             # SQLAlchemy ORM 模型
│   │   └── base.py
│   ├── schemas/            # Pydantic 请求/响应 Schema
│   ├── routers/            # FastAPI 路由
│   ├── services/           # 业务逻辑层
│   ├── repositories/       # 数据访问层（Repository Pattern）
│   ├── events/             # RabbitMQ 发布/消费
│   └── dependencies.py     # FastAPI 依赖注入
├── tests/
│   ├── unit/               # 单元测试
│   └── integration/        # 集成测试
├── alembic/                # 数据库迁移
│   ├── versions/
│   └── env.py
├── requirements.txt
├── Dockerfile
└── README.md
```

---
title: 术语表
---

| 术语 | 说明 |
|------|------|
| **BFF** | Backend For Frontend，面向特定前端的聚合层，减少客户端请求次数 |
| **API Gateway** | 统一流量入口，负责 JWT 鉴权、限流、路由转发 |
| **Saga** | 分布式事务编排模式，通过一系列本地事务和补偿操作保证最终一致性 |
| **SPU** | Standard Product Unit，标准产品单元，如"Nike Air Max 2024" |
| **SKU** | Stock Keeping Unit，库存单元，如"Nike Air Max 2024 红色 42码" |
| **RBAC** | Role-Based Access Control，基于角色的访问控制 |
| **JWT** | JSON Web Token，无状态身份认证令牌 |
| **Routing Key** | RabbitMQ 中事件路由的键，如 `order.created` |
| **Database per Service** | 每个微服务拥有独立数据库（Schema），数据隔离 |
| **幂等性** | 相同请求多次执行结果与执行一次相同，通过 `request_id` 实现 |
| **熔断器** | Circuit Breaker，防止故障级联扩散的保护机制 |
| **Kustomize** | Kubernetes 原生配置管理工具，支持多环境 overlay |
| **Terraform** | 基础设施即代码工具，管理云资源 |
| **structlog** | Python 结构化日志库，输出 JSON 格式日志 |
| **asyncpg** | PostgreSQL 的高性能异步 Python 驱动 |
| **uv** | 快速 Python 包安装与解析工具 |
| **隐私号** | 虚拟中间号码，保护买卖双方真实手机号不被对方知晓 |
| **Prometheus** | 开源监控与告警系统，通过拉取指标端点采集数据 |
| **Elasticsearch** | 分布式搜索引擎，用于商品全文检索 |
| **bcrypt** | 密码哈希算法，含 salt，具有自适应计算开销 |
| **access_token** | 短期访问令牌（默认 30 分钟），用于 API 鉴权 |
| **request_id** | 请求唯一 ID，贯穿整个调用链路，用于日志追踪和幂等控制 |

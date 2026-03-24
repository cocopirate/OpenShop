# 架构设计文档

## 1. 整体架构

OpenShop 采用微服务架构，各服务职责单一，通过 Kubernetes DNS 进行服务发现，通过 Kafka 进行异步事件驱动通信。

## 2. 分层设计

### 入口层
- **API Gateway（:8080）**：统一流量入口，负责 JWT 鉴权、限流、路由转发。
- **App BFF（:8090）**：聚合移动端所需接口，减少客户端请求次数。
- **Admin BFF（:8091）**：聚合管理后台所需接口，支持 RBAC 权限控制。

### 编排层
- **Order Orchestration（:8100）**：使用 Saga 模式编排订单创建的分布式事务，确保数据一致性。

### 领域服务层
各领域服务独立部署，拥有自己的 PostgreSQL Schema，遵循 Database per Service 模式。

### 能力服务层
提供与业务无关的技术能力（短信、隐私号），供上层服务调用。

## 3. 通信模式

| 场景 | 模式 | 技术 |
|------|------|------|
| 同步查询 | 请求/响应 | HTTP (httpx) |
| 异步事件 | 发布/订阅 | Kafka |
| 缓存 | 旁路缓存 | Redis |
| 搜索 | 全文检索 | Elasticsearch |

## 4. 服务发现

使用 Kubernetes 原生 DNS，服务通过 `{service-name}.{namespace}.svc.cluster.local` 相互访问，无需额外注册中心。

## 5. 配置管理

- 非敏感配置：Kubernetes ConfigMap
- 敏感配置（DB 密码、API Key）：Kubernetes Secret
- 本地开发：`.env` 文件（由 pydantic-settings 读取）

# lead-service（客资订单服务）

版本：v1.0.0
端口：`:8012`

## 功能概述

管理销售线索（客资订单）的完整生命周期，包括创建、查询、状态流转。

## 状态流转

```
用户提交表单
      │
      ▼
  [pending] 待处理
   │         │
   │         └──── 用户/商家取消 ──▶ [cancelled] 已取消
   │
   └──── 商家标记转化 ──▶ [converted] 已转化
```

`converted` 和 `cancelled` 均为终态，不可再流转。

## 主要接口

### 用户侧

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/leads` | 提交客资表单（1分钟内幂等） |
| `GET` | `/api/v1/leads` | 查询客资列表（手机号脱敏） |
| `GET` | `/api/v1/leads/{lead_id}` | 查询客资详情 |
| `PATCH` | `/api/v1/leads/{lead_id}/cancel` | 取消客资 |

### 商家侧

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/leads` | 分页查询（支持状态/城市过滤） |
| `PATCH` | `/api/v1/leads/{lead_id}/convert` | 标记已转化 |
| `PATCH` | `/api/v1/leads/{lead_id}/cancel` | 标记取消 |
| `GET` | `/api/v1/leads/{lead_id}/logs` | 查询状态变更日志 |

### 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 健康检查（含 DB + Redis） |
| `GET` | `/health/ready` | K8s Readiness Probe |

## 数据模型

- **LeadOrder**：客资主表，含 phone、city、district、product_ids（JSONB）、status、source 等
- **LeadStatusLog**：状态变更日志，记录每次状态流转的操作人和时间

## 配置项

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `DATABASE_URL` | – | PostgreSQL 连接串 |
| `REDIS_URL` | – | Redis 连接串 |
| `RABBITMQ_URL` | `amqp://guest:guest@localhost:5672/` | RabbitMQ 地址 |
| `PRODUCT_SERVICE_URL` | `http://product-service:8003` | product-service 地址 |
| `ORDER_SERVICE_URL` | `http://order-service:8005` | order-service 地址 |
| `SERVICE_PORT` | `8012` | 服务端口 |

## 依赖服务

| 服务 | 通信方式 | 用途 |
|------|----------|------|
| `product-service` (:8003) | HTTP（同步） | 校验 product_ids 有效性 |
| `notification-service` (:8009) | RabbitMQ（异步） | 发布 `lead.submitted` 事件触发短信回执 |

## 事件

发布 `lead.submitted` 到 RabbitMQ openshop topic exchange：

```json
{
  "event": "lead.submitted",
  "lead_id": "uuid-lead-001",
  "phone": "13800138000",
  "product_ids": ["uuid-product-1"],
  "created_at": "2026-04-04T10:00:00Z"
}
```

## 非功能特性

- **手机号脱敏**：列表接口返回 `138****0000` 格式
- **幂等性**：同一手机号 + 商品在 1 分钟内重复提交返回已有客资
- **数据库迁移**：Alembic 管理，版本表 `alembic_version_lead`

## 本地开发

```bash
cp .env.example .env
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8012
```

## 测试

```bash
pip install pytest pytest-asyncio httpx
pytest tests/
```

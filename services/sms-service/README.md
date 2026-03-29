# sms-service（短信能力服务）

统一封装第三方短信供应商，提供验证码发送与校验、模板管理、多租户渠道路由和运行时配置管理能力。

## 目录结构

```
sms-service/
├── app/
│   ├── api/v1/
│   │   └── router.py         # 全部路由（发送/验证/模板/渠道/客户端Key/配置）
│   ├── core/
│   │   ├── config.py         # pydantic-settings 配置
│   │   ├── database.py       # SQLAlchemy 异步引擎 + 会话
│   │   ├── redis.py          # aioredis 连接池
│   │   ├── rate_limiter.py   # Redis 滑动窗口限频
│   │   ├── metrics.py        # Prometheus 指标
│   │   ├── tracing.py        # OpenTelemetry 链路追踪
│   │   ├── logging.py        # structlog 结构化日志
│   │   ├── masking.py        # 手机号脱敏
│   │   └── response.py       # 统一响应格式
│   ├── models/
│   │   ├── sms_record.py     # SmsRecord ORM 模型
│   │   ├── sms_template.py   # SmsTemplate ORM 模型
│   │   └── sms_config_store.py  # SmsConfigStore 持久化配置表（id=1 单行）
│   ├── schemas/
│   │   └── sms.py            # Pydantic 请求/响应 schema
│   ├── services/
│   │   ├── sms_service.py    # 核心业务逻辑（发送/验证/幂等）
│   │   └── admin_service.py  # 模板 CRUD + 渠道/客户端 Key CRUD + 配置管理
│   ├── providers/
│   │   ├── __init__.py       # BaseSmsProvider / SendResult / StatusResult
│   │   ├── factory.py        # 供应商工厂 + 熔断器
│   │   ├── aliyun.py         # 阿里云短信（REST 签名）
│   │   ├── aliyun_phone_svc.py  # 阿里云号码认证服务（SDK）
│   │   ├── tencent.py        # 腾讯云短信
│   │   └── chuanglan.py      # 创蓝云短信（253.com）
│   └── main.py               # FastAPI 应用入口 + 生命周期
├── alembic/                  # 数据库迁移脚本
├── tests/                    # pytest 测试
├── deploy/                   # K8s Deployment + Service YAML
├── pyproject.toml
├── requirements.txt
└── .env.example
```

## HTTP 接口

### 短信发送

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/sms/send` | 发送短信（支持幂等 `request_id` 和渠道路由 `channel`） |
| `POST` | `/api/sms/send-code` | 发送验证码（需 `X-API-Key` 请求头，若配置了 `SMS_CLIENT_KEYS`） |
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

### 配置管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/sms/config` | 查询运行时配置（供应商凭据已脱敏） |
| `PUT` | `/api/sms/config` | 批量更新配置（供应商凭据、限频、熔断器参数等）；变更立即生效并**持久化到 DB**，重启后自动恢复 |

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
| `GET` | `/health` | 服务健康（含 DB / Redis 连通性） |
| `GET` | `/health/ready` | K8s Readiness Probe |
| `GET` | `/metrics` | Prometheus 指标 |

## 数据模型

**SmsRecord** – 每次发送的结果记录，含供应商返回 ID、状态、错误信息；手机号脱敏存储。到期由后台任务自动清理（`SMS_RECORDS_RETENTION_DAYS`）。

**SmsTemplate** – 供应商模板 ID 与本地名称的映射，支持多供应商、启用/禁用状态。

**SmsConfigStore** – 单行 JSON 配置表（id=1），持久化所有运行时配置（供应商凭据、限频参数、熔断器参数、渠道路由、客户端 API Key 等）。服务启动时加载此表并覆盖默认值。

## 供应商

通过 `SMS_PROVIDER` 指定默认供应商：

| 值 | 供应商 | 凭据环境变量前缀 |
|----|--------|----------------|
| `chuanglan` | 创蓝云（253.com，默认） | `CHUANGLAN_` |
| `aliyun` | 阿里云短信服务（Dysms REST） | `ALIYUN_` |
| `aliyun_phone_svc` | 阿里云号码认证服务（PNS SDK） | `ALIYUN_PHONE_SVC_` |
| `tencent` | 腾讯云短信 | `TENCENT_` |

### 熔断器（Circuit Breaker）

主供应商连续失败 `SMS_PROVIDER_FAILURE_THRESHOLD` 次后熔断，自动切换到 `SMS_PROVIDER_FALLBACK`；经过 `SMS_PROVIDER_RECOVERY_TIMEOUT` 秒后进入半开状态尝试恢复。进程级内存状态，重启后重置。

### 多租户渠道路由

渠道（Channel）为不同业务方提供独立的供应商和凭据；客户端 API Key 将外部请求的 `X-API-Key` 映射到渠道名称。两者均通过管理后台 API **持久化到数据库**，服务重启后自动恢复。

配置了至少一条客户端 Key 后，`POST /api/sms/send-code` 必须携带合法的 `X-API-Key` 请求头。

```
外部 A 业务  →  X-API-Key: key-a  →  business_a 渠道  →  aliyun_phone_svc（独立密钥）
外部 B 业务  →  X-API-Key: key-b  →  business_b 渠道  →  aliyun（独立密钥）
内部服务     →  不传 X-API-Key   →  全局 SMS_PROVIDER（默认渠道）
```

```bash
# 创建渠道
curl -X PUT http://localhost:8010/api/sms/channels/business_a \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "aliyun_phone_svc",
    "access_key_id": "k1",
    "access_key_secret": "s1",
    "sign_name": "A业务",
    "endpoint": "dypnsapi.aliyuncs.com"
  }'

# 绑定客户端 API Key → 渠道
curl -X POST http://localhost:8010/api/sms/client-keys \
  -H "Content-Type: application/json" \
  -d '{"api_key": "key-a-001", "channel": "business_a"}'
```

## 核心机制

### 验证码流程

1. `POST /api/sms/send-code` 生成 6 位 OTP，写入 Redis（TTL = `SMS_CODE_TTL`）
2. 调用供应商发送短信
3. `POST /api/sms/verify` 从 Redis 读取并比对，验证成功后立即删除 key

### 幂等发送

`POST /api/sms/send` 支持 `request_id` 字段（最大 64 字符）。同一 `request_id` 的重复请求直接返回首次发送结果，Redis 缓存 24 小时。

### 限频（Redis 滑动窗口）

同时检查两个维度：

| 维度 | 每分钟 | 每日 |
|------|--------|------|
| 手机号 | `SMS_RATE_LIMIT_PHONE_PER_MINUTE` | `SMS_RATE_LIMIT_PHONE_PER_DAY` |
| 来源 IP | `SMS_RATE_LIMIT_IP_PER_MINUTE` | `SMS_RATE_LIMIT_IP_PER_DAY` |

超限时返回 `HTTP 429`，响应头含 `Retry-After`。

## 配置参考

SMS 供应商相关配置（凭据、限频、熔断器参数、渠道路由、客户端 Key 等）**不通过环境变量管理**，全部使用管理后台 API 写入数据库并持久化。服务重启时自动从 `sms_config_store` 表恢复，无需任何 SMS 相关的 `.env` 条目。

`.env` 只需配置基础设施连接信息：

```bash
# 服务基础
SERVICE_PORT=8010
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
RABBITMQ_URL=amqp://...

# OpenTelemetry（留空禁用）
OTEL_ENDPOINT=
OTEL_TOKEN=
```

完整 env 示例见 `.env.example`。

### 首次部署：通过 API 写入供应商配置

```bash
# 配置创蓝云为默认供应商
curl -X PUT http://localhost:8010/api/sms/config \
  -H "Content-Type: application/json" \
  -d '{"sms_provider": "chuanglan", "chuanglan": {"account": "xxx", "password": "xxx"}}'

# 配置阿里云号码认证服务
curl -X PUT http://localhost:8010/api/sms/config \
  -H "Content-Type: application/json" \
  -d '{
    "sms_provider": "aliyun_phone_svc",
    "aliyun_phone_svc": {
      "access_key_id": "your_key_id",
      "access_key_secret": "your_key_secret",
      "sign_name": "你的签名",
      "endpoint": "dypnsapi.aliyuncs.com"
    }
  }'

# 配置限频和熔断器参数
curl -X PUT http://localhost:8010/api/sms/config \
  -H "Content-Type: application/json" \
  -d '{
    "sms_rate_limit_phone_per_minute": 1,
    "sms_rate_limit_phone_per_day": 10,
    "sms_provider_failure_threshold": 3,
    "sms_provider_recovery_timeout": 60
  }'
```

### 首次部署：多租户渠道路由配置

```bash
# 新建渠道（全量写入）
curl -X PUT http://localhost:8010/api/sms/channels/business_a \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "aliyun_phone_svc",
    "access_key_id": "k1",
    "access_key_secret": "s1",
    "sign_name": "A业务"
  }'

# 局部更新渠道（只改 sign_name）
curl -X PATCH http://localhost:8010/api/sms/channels/business_a \
  -H "Content-Type: application/json" \
  -d '{"sign_name": "新签名"}'

# 绑定客户端 API Key → 渠道
curl -X POST http://localhost:8010/api/sms/client-keys \
  -H "Content-Type: application/json" \
  -d '{"api_key": "key-a-001", "channel": "business_a"}'

# 查询当前渠道列表
curl http://localhost:8010/api/sms/channels

# 删除渠道
curl -X DELETE http://localhost:8010/api/sms/channels/business_a

# 删除客户端 Key
curl -X DELETE http://localhost:8010/api/sms/client-keys/key-a-001
```

## 本地开发

```bash
# 1. 启动依赖（PostgreSQL + Redis）
docker-compose -f ../../infra/docker-compose.yml up -d postgres redis

# 2. 创建虚拟环境并安装依赖
uv venv --python 3.11
uv pip install -r requirements.txt
source .venv/bin/activate

# 3. 配置环境变量
cp .env.example .env

# 4. 应用数据库迁移
alembic upgrade head

# 5. 启动服务
uvicorn app.main:app --reload --port 8010
```

### 数据库迁移

```bash
# 应用迁移
alembic upgrade head

# 生成新迁移（修改 ORM 模型后）
alembic revision --autogenerate -m "描述"
```

### 运行测试

```bash
pytest tests/ -v
```

## K8s 部署

```bash
kubectl apply -f deploy/deployment.yaml
kubectl apply -f deploy/service.yaml
```

- Readiness Probe：`GET /health/ready`
- Liveness Probe：`GET /health`
- 端口：**8010**

## 可观测性

| 能力 | 实现 |
|------|------|
| 结构化日志 | structlog（JSON 格式） |
| 指标 | Prometheus，`GET /metrics` |
| 链路追踪 | OpenTelemetry（OTLP），`OTEL_ENDPOINT` 为空时禁用 |

## 依赖服务

- **PostgreSQL** – 发送记录和模板持久化
- **Redis** – 验证码缓存、幂等 key、限频滑动窗口
- **RabbitMQ**（可选）– 消息消费（`RABBITMQ_URL` 配置）
- **notification-service** – 上游调用方

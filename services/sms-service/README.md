# sms-service（短信能力服务）

对接第三方短信供应商（阿里云、腾讯云），提供统一短信发送能力。

## 目录结构

```
sms-service/
├── app/
│   ├── api/v1/       # 路由层
│   ├── core/         # 配置、数据库、Redis 依赖注入
│   ├── models/       # SQLAlchemy ORM 模型
│   ├── schemas/      # Pydantic 请求/响应模型
│   ├── services/     # 业务逻辑
│   └── providers/    # 通道适配器（阿里云 / 腾讯云）
├── alembic/          # 数据库迁移
├── tests/            # 单元 / 集成测试
├── deploy/           # K8s YAML（Deployment + Service）
├── pyproject.toml    # uv 依赖管理
├── requirements.txt  # pip 锁定版本
└── .env.example      # 本地环境变量模板
```

## 主要接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `POST /api/v1/sms/send` | POST | 发送短信 |
| `POST /api/v1/sms/send-code` | POST | 发送验证码短信 |
| `GET  /api/v1/sms/records` | GET | 查询发送记录（手机号/时间/状态过滤 + 分页） |
| `POST /api/v1/sms/verify` | POST | 验证短信验证码 |
| `GET  /health` | GET | 服务健康检查（含 DB / Redis 连通性） |
| `GET  /health/ready` | GET | K8s Readiness Probe |

## 管理后台接口（Admin API）

> 以下接口前缀为 `/api/v1/admin`，仅限管理员调用。鉴权由 API Gateway 的 RBAC 层负责，
> 请求到达 sms-service 前须通过角色验证。

### 发送记录管理

| 接口 | 方法 | 说明 |
|------|------|------|
| `GET  /api/v1/admin/sms/records` | GET | 查询短信发送记录（支持手机号/时间/状态过滤 + 分页） |
| `DELETE /api/v1/admin/sms/records/{id}` | DELETE | 删除指定发送记录 |

### 短信模板管理

| 接口 | 方法 | 说明 |
|------|------|------|
| `GET  /api/v1/admin/sms/templates` | GET | 查询模板列表（支持供应商/状态过滤 + 分页） |
| `POST /api/v1/admin/sms/templates` | POST | 创建短信模板 |
| `GET  /api/v1/admin/sms/templates/{id}` | GET | 获取模板详情 |
| `PUT  /api/v1/admin/sms/templates/{id}` | PUT | 更新短信模板 |
| `DELETE /api/v1/admin/sms/templates/{id}` | DELETE | 删除短信模板 |

### 短信配置管理

| 接口 | 方法 | 说明 |
|------|------|------|
| `GET  /api/v1/admin/sms/config` | GET | 查询当前短信服务配置（供应商、限频、熔断器参数等） |
| `PUT  /api/v1/admin/sms/config` | PUT | 动态更新短信服务配置（运行时生效，重启后恢复至环境变量值） |

## 数据模型

- **SmsRecord** – 发送记录表，记录每次发送的状态、供应商响应 ID 等
- **SmsTemplate** – 模板表，维护供应商模板 ID 与本地名称映射

## 基础设施接入

### 配置管理

所有配置通过环境变量或 `.env` 文件注入，使用 `pydantic-settings` 统一管理：

```bash
cp .env.example .env
# 编辑 .env，填入真实值
```

各环境模板：
- `.env.example` – 本地开发（docker-compose 默认值）
- `.env.staging.example` – 预发布环境
- `.env.prod.example` – 生产环境

### 数据库迁移（Alembic）

```bash
# 应用初始迁移（创建 sms_records、sms_templates 表）
alembic upgrade head

# 生成新迁移（修改模型后）
alembic revision --autogenerate -m "描述"
```

### 本地开发

```bash
# 启动依赖（PostgreSQL + Redis）
docker-compose -f ../../infra/docker-compose.yml up -d postgres redis

# 安装依赖（推荐使用 uv）
uv pip install -r requirements.txt
# 或：pip install -r requirements.txt

# 应用数据库迁移
alembic upgrade head

# 启动服务
uvicorn app.main:app --reload --port 8010
```

### 运行测试

```bash
pytest tests/ -v
```

### K8s 部署

```bash
kubectl apply -f deploy/deployment.yaml
kubectl apply -f deploy/service.yaml
```

Readiness Probe 指向 `GET /health/ready`，Liveness Probe 指向 `GET /health`。

## SMS 供应商

通过 `SMS_PROVIDER` 环境变量切换：
- `aliyun`（默认）– 阿里云短信服务
- `tencent` – 腾讯云短信
- `chuanglan` – 创蓝云短信（253.com）

支持通过 `SMS_PROVIDER_FALLBACK` 配置备用供应商，主供应商故障时自动切换（熔断器模式）。

## 依赖服务

- notification-service（上游调用方）

## 端口

- 服务端口: **8010**

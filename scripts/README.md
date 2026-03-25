# scripts（运维脚本）

## 脚本列表

| 脚本 | 说明 |
|------|------|
| `health-check.sh` | 检查所有服务的 `/health` 端点是否正常响应 |
| `start-all.sh` | 本地开发环境一键启动基础设施与所有服务 |

---

## 快速开始 / Quick Start

### 前置条件

| 工具 | 版本要求 | 安装方式 |
|------|----------|----------|
| Docker & Docker Compose | 24+ | [https://docs.docker.com/get-docker/](https://docs.docker.com/get-docker/) |
| Python | 3.11+ | [https://www.python.org/downloads/](https://www.python.org/downloads/) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

### 一键启动

```bash
# 在项目根目录执行
./scripts/start-all.sh
```

启动脚本会自动完成以下步骤：

1. **启动基础设施**（PostgreSQL / Redis / Kafka）— 通过 `infra/docker-compose.yml`
2. **等待基础设施就绪**（10 秒）
3. 对每个服务依次执行：
   - 创建 Python 3.11 虚拟环境（`.venv`，若不存在）
   - 安装 / 同步依赖（`uv pip install -r requirements.txt`）
   - 从 `.env.example` 初始化 `.env`（若 `.env` 不存在）
   - 执行数据库迁移（`alembic upgrade head`，仅限已配置 Alembic 的服务）
   - 后台启动 uvicorn（`--reload` 热重载模式）

### 验证服务状态

```bash
./scripts/health-check.sh
```

---

## 单服务手动启动 / Single Service Startup

以 `user-service` 为例，其他服务流程相同（端口号见下表）：

```bash
cd services/user-service

# 1. 安装 uv（如未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 创建虚拟环境 + 安装依赖
uv venv --python 3.11
uv pip install -r requirements.txt

# 3. 激活虚拟环境
source .venv/bin/activate

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env，填入真实的密钥和连接字符串

# 5. 执行数据库迁移（仅适用于有 alembic.ini 的服务）
alembic upgrade head

# 6. 启动服务
uvicorn app.main:app --port <PORT> --reload
```

---

## 服务端口一览 / Service Ports

| 服务 | 路径 | 端口 | 数据库迁移 |
|------|------|------|------------|
| api-gateway | `bff/api-gateway` | 8080 | — |
| order-orchestration | `orchestration/order-orchestration` | 8100 | — |
| user-service | `services/user-service` | 8001 | ✅ Alembic |
| merchant-service | `services/merchant-service` | 8002 | — |
| product-service | `services/product-service` | 8003 | — |
| inventory-service | `services/inventory-service` | 8004 | — |
| order-service | `services/order-service` | 8005 | — |
| aftersale-service | `services/aftersale-service` | 8006 | — |
| promotion-service | `services/promotion-service` | 8007 | — |
| location-service | `services/location-service` | 8008 | — |
| notification-service | `services/notification-service` | 8009 | — |
| sms-service | `services/sms-service` | 8010 | ✅ Alembic |
| virtual-number-service | `services/virtual-number-service` | 8011 | — |

---

## 停止所有服务 / Stop All Services

```bash
# 停止后台 uvicorn 进程
pkill -f uvicorn || true

# 停止基础设施容器
docker-compose -f infra/docker-compose.yml down
```

---

## 常见问题 / FAQ

**Q: 启动时报 `uv: command not found`？**  
A: 安装 uv 后需重新加载 shell 配置：`source $HOME/.local/bin/env` 或重新打开终端。

**Q: alembic 迁移失败？**  
A: 确认 `.env` 中的 `DATABASE_URL` 已正确配置，且 PostgreSQL 容器已正常运行（`docker-compose -f infra/docker-compose.yml ps`）。

**Q: 端口被占用？**  
A: 使用 `lsof -i :<PORT>` 查找占用进程并终止，或修改 `.env` 中的 `SERVICE_PORT` 与启动命令的端口号。

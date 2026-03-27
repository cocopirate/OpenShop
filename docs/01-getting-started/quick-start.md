# 快速启动

## 前置要求

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) 包管理工具
- Docker & Docker Compose 24+
- （可选）kubectl + 已配置的 Kubernetes 集群

## 1. 克隆项目

```bash
git clone https://github.com/cocopirate/OpenShop.git
cd OpenShop
```

## 2. 配置环境变量

```bash
cp .env.example .env
# 根据实际情况修改 .env 中的数据库、Redis、RabbitMQ 连接信息
```

## 3. 启动基础设施

```bash
docker-compose -f infra/docker-compose.yml up -d
```

启动以下服务：
- PostgreSQL 16（端口 5432）
- Redis 7（端口 6379）
- RabbitMQ 3.13（端口 5672 / 管理 UI 15672）
- Elasticsearch 8（端口 9200）

## 4. 启动所有微服务

```bash
./scripts/start-all.sh
```

脚本会自动：
1. 创建 Python 虚拟环境（`.venv`）
2. 使用 `uv pip install` 安装依赖
3. 运行数据库迁移（Alembic）
4. 以热重载模式启动所有服务

## 5. 验证服务健康状态

```bash
./scripts/health-check.sh
```

## 6. 访问 API 文档

| 服务 | Swagger UI |
|------|-----------|
| api-gateway | http://localhost:8080/docs |
| app-bff | http://localhost:8090/docs |
| admin-bff | http://localhost:8091/docs |
| user-service | http://localhost:8001/docs |

详细的本地开发指南请参阅 [本地开发](local-dev.md)。

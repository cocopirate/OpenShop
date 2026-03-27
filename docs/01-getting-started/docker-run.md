# Docker 运行

## 使用 Docker Compose 启动完整环境

### 基础设施服务

```bash
# 启动所有基础设施
docker-compose -f infra/docker-compose.yml up -d

# 查看服务状态
docker-compose -f infra/docker-compose.yml ps

# 查看日志
docker-compose -f infra/docker-compose.yml logs -f rabbitmq
```

### docker-compose.yml 服务清单

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| postgres | postgres:16-alpine | 5432 | 主数据库 |
| redis | redis:7-alpine | 6379 | 缓存，密码 `redis123` |
| rabbitmq | rabbitmq:3.13-management | 5672 / 15672 | 消息队列 |
| elasticsearch | elasticsearch:8.13.0 | 9200 | 搜索引擎 |

### 访问 RabbitMQ 管理界面

```
http://localhost:15672
用户名: openshop
密码: openshop123
```

### 访问 Elasticsearch

```bash
curl http://localhost:9200/_cluster/health?pretty
```

## 单独构建服务镜像

每个服务目录下均有 `Dockerfile`：

```bash
# 以 user-service 为例
cd services/user-service
docker build -t openshop/user-service:latest .

# 运行容器
docker run -d \
  --name user-service \
  -p 8001:8001 \
  --env-file ../../.env \
  openshop/user-service:latest
```

## 停止与清理

```bash
# 停止所有服务
docker-compose -f infra/docker-compose.yml down

# 停止并删除数据卷（清空数据库）
docker-compose -f infra/docker-compose.yml down -v
```

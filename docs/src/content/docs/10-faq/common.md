---
title: 常见问题
---

## Q: 如何本地启动所有服务？

```bash
# 1. 启动基础设施
docker-compose -f infra/docker-compose.yml up -d

# 2. 启动所有服务
./scripts/start-all.sh
```

详见 [快速启动](../01-getting-started/quick-start.md)。

## Q: 如何只启动某一个服务？

```bash
cd services/consumer-service
uvicorn app.main:app --reload --port 8001
```

## Q: JWT Token 如何获取？

```bash
curl -X POST http://localhost:8000/api/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}'
```

## Q: 如何查看各服务的 API 文档？

本地开发时，访问各服务的 Swagger UI：

| 服务 | 地址 |
|------|------|
| api-gateway | http://localhost:8080/docs |
| auth-service | http://localhost:8000/docs |
| admin-service | http://localhost:8012/docs |
| consumer-service | http://localhost:8001/docs |
| order-service | http://localhost:8005/docs |
| sms-service | http://localhost:8010/docs |

## Q: 数据库迁移如何执行？

```bash
cd services/consumer-service
alembic upgrade head
```

## Q: 如何查看 RabbitMQ 消息队列状态？

访问 RabbitMQ 管理界面：http://localhost:15672  
用户名/密码：`openshop` / `openshop123`

## Q: 如何切换短信供应商？

```bash
# 方式一：修改环境变量（重启后生效）
SMS_PROVIDER=tencent

# 方式二：运行时 API（重启后恢复）
curl -X PUT http://localhost:8010/api/v1/admin/sms/config \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"sms_provider": "tencent"}'
```

## Q: 本地开发环境如何重置数据库？

```bash
# 停止并删除数据卷（清空所有数据）
docker-compose -f infra/docker-compose.yml down -v

# 重新启动
docker-compose -f infra/docker-compose.yml up -d

# 重新执行迁移
cd services/consumer-service && alembic upgrade head
```

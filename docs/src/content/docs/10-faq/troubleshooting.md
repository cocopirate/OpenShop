---
title: 故障排查
---

## 服务无法启动

**症状**：服务启动报错，无法访问 API

**排查步骤**：

1. 检查环境变量是否正确配置：
   ```bash
   cat .env
   ```

2. 检查基础设施是否正常运行：
   ```bash
   docker-compose -f infra/docker-compose.yml ps
   ```

3. 查看服务日志：
   ```bash
   # 本地
   uvicorn app.main:app --reload --port 8001
   
   # Kubernetes
   kubectl logs -f deployment/consumer-service -n openshop
   ```

## 数据库连接失败

**症状**：启动时报 `asyncpg.exceptions.ConnectionDoesNotExistError`

**排查**：
- 检查 `DATABASE_URL` 是否正确
- 确认 PostgreSQL 容器正在运行：`docker ps | grep postgres`
- 测试连接：`psql postgresql://openshop:openshop123@localhost:5432/openshop`

## JWT 鉴权失败（401）

**症状**：携带 Token 请求返回 401

**可能原因**：
1. Token 已过期（默认 30 分钟）→ 重新登录获取新 Token
2. 用户账号被禁用 → 联系管理员检查账号状态
3. 权限版本变更（角色/权限被修改）→ 重新登录

**调试**：
```bash
# 解码 JWT（不验证签名）
echo "eyJhbGci..." | cut -d. -f2 | base64 -d
```

## RabbitMQ 消息积压

**症状**：消息队列深度持续增长，消费者未处理

**排查**：
1. 访问管理界面：http://localhost:15672
2. 查看 Queues 列表，找到积压队列
3. 检查消费者服务日志，查看是否有报错

**处理**：
- 如消费者崩溃，重启对应服务
- 如消息处理失败，检查死信队列（Dead Letter Queue）

## 短信发送失败

**症状**：短信 API 返回错误或用户未收到短信

**排查**：
1. 查看 sms-service 日志，确认供应商响应
2. 检查是否触发限流（`sms_rate_limit` 相关日志）
3. 检查熔断器状态：
   ```bash
   GET /api/v1/admin/sms/config  # 查看当前运行时配置
   ```
4. 尝试切换到备用供应商

## Kubernetes Pod 重启循环（CrashLoopBackOff）

```bash
# 查看 Pod 状态
kubectl get pods -n openshop

# 查看崩溃日志（最近的日志）
kubectl logs consumer-service-6d4b9f5-xyz -n openshop --previous

# 查看 Pod 详情（查看事件）
kubectl describe pod consumer-service-6d4b9f5-xyz -n openshop
```

常见原因：
- 环境变量或 Secret 缺失
- 数据库连接失败（健康检查不通过）
- 内存不足（OOMKilled）

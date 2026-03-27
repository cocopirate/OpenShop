# 环境变量

## 公共环境变量

所有服务共享以下环境变量：

| 变量 | 说明 | 示例 |
|------|------|------|
| `DATABASE_URL` | PostgreSQL 连接串（asyncpg） | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | Redis 连接串 | `redis://:password@localhost:6379/0` |
| `RABBITMQ_URL` | RabbitMQ 连接串 | `amqp://user:pass@localhost:5672/` |
| `SECRET_KEY` | JWT 签名密钥 | 随机字符串，≥32 位 |
| `DEBUG` | 调试模式 | `true` / `false` |
| `LOG_LEVEL` | 日志级别 | `INFO` / `DEBUG` |

## 短信服务专用变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SMS_PROVIDER` | 主供应商 | `aliyun` |
| `SMS_PROVIDER_FALLBACK` | 备用供应商 | `tencent` |
| `SMS_PROVIDER_FAILURE_THRESHOLD` | 熔断阈值（连续失败次数） | `3` |
| `SMS_PROVIDER_RECOVERY_TIMEOUT` | 熔断恢复等待时间（秒） | `60` |
| `SMS_CODE_TTL` | 验证码有效期（秒） | `300` |
| `SMS_RATE_LIMIT_PHONE_PER_MINUTE` | 单手机号每分钟限频 | `1` |
| `SMS_RATE_LIMIT_PHONE_PER_DAY` | 单手机号每日限频 | `10` |
| `SMS_RATE_LIMIT_IP_PER_MINUTE` | 单 IP 每分钟限频 | `10` |
| `SMS_RATE_LIMIT_IP_PER_DAY` | 单 IP 每日限频 | `100` |
| `SMS_RECORDS_RETENTION_DAYS` | 发送记录保留天数（0=永久） | `90` |
| `ALIYUN_ACCESS_KEY_ID` | 阿里云 AccessKey ID | — |
| `ALIYUN_ACCESS_KEY_SECRET` | 阿里云 AccessKey Secret | — |
| `ALIYUN_SIGN_NAME` | 阿里云短信签名 | — |

## 本地开发配置

```bash
# 复制模板
cp .env.example .env

# 编辑 .env
DATABASE_URL=postgresql+asyncpg://openshop:openshop123@localhost:5432/openshop
REDIS_URL=redis://:redis123@localhost:6379/0
RABBITMQ_URL=amqp://openshop:openshop123@localhost:5672/
SECRET_KEY=dev-secret-key-change-in-production
DEBUG=true
LOG_LEVEL=DEBUG
```

## Kubernetes 配置管理

- **非敏感配置**（LOG_LEVEL、DEBUG 等）：存放在 Kubernetes **ConfigMap**
- **敏感配置**（SECRET_KEY、数据库密码、API Key 等）：存放在 Kubernetes **Secret**

```yaml
# 示例：Secret 配置
apiVersion: v1
kind: Secret
metadata:
  name: openshop-secrets
  namespace: openshop
type: Opaque
data:
  SECRET_KEY: <base64-encoded-value>
  DATABASE_URL: <base64-encoded-value>
```

> ⚠️ **禁止将 `.env` 文件、密钥或 Secret 提交到 Git 仓库。**

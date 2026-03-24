# Terraform 基础设施

## 职责

使用 IaC（基础设施即代码）管理云资源，包括：

- VPC / 子网 / 安全组
- 数据库实例（RDS）
- 缓存实例（Redis）
- 消息队列（RabbitMQ / Kafka）
- 对象存储（OSS / S3）

## 使用方式

```bash
cd infra/terraform
tf init
tf plan
tf apply
```
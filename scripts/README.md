# Scripts

## 目录说明

常用运维与开发脚本集合。

## 脚本列表

| 脚本 | 说明 |
|------|------|
| `start-all.sh` | 本地一键启动所有服务（基于 docker-compose） |
| `stop-all.sh` | 停止所有本地服务 |
| `build-all.sh` | 构建所有服务镜像 |
| `db-migrate.sh` | 执行数据库迁移脚本 |
| `health-check.sh` | 检查所有服务健康状态 |

## 使用方式

```bash
chmod +x scripts/*.sh
./scripts/start-all.sh
./scripts/health-check.sh
```
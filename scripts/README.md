# scripts（运维脚本）

## 脚本列表

| 脚本 | 说明 |
|------|------|
| `health-check.sh` | 检查所有服务的 `/health` 端点是否正常响应 |
| `start-all.sh` | 本地开发环境一键启动基础设施与所有服务 |

## 使用说明

```bash
# 健康检查
./scripts/health-check.sh

# 一键启动（需要本地已安装 Docker、Python 3.11+、uvicorn）
./scripts/start-all.sh
```

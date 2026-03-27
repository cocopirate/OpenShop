# CI/CD

## GitHub Actions 工作流

项目使用 GitHub Actions 进行持续集成和持续部署。

### 文档发布（docs.yml）

每次推送 `docs/**` 目录的变更时，自动将文档发布到 GitHub Pages：

```yaml
on:
  push:
    branches: [main]
    paths: ['docs/**']
```

访问地址：https://cocopirate.github.io/OpenShop/

## 推荐的 CI 流程

以下为建议的完整 CI 流程（可按需扩展）：

```
代码推送 / PR
    │
    ├── lint（ruff check）
    ├── type-check（mypy）
    ├── unit-tests（pytest tests/unit/）
    └── integration-tests（pytest tests/integration/，需要 DB/Redis）

合并到 main
    │
    ├── 构建 Docker 镜像
    ├── 推送到镜像仓库
    └── 触发 Kubernetes 滚动更新
```

## 本地 CI 模拟

```bash
# 代码格式检查
ruff format --check .
ruff check .

# 运行测试
pytest tests/ -v --cov=app --cov-report=term-missing

# 构建 Docker 镜像
docker build -t openshop/consumer-service:latest services/consumer-service/
```

## 镜像版本策略

| 标签 | 说明 |
|------|------|
| `latest` | 最新 main 分支构建 |
| `v1.2.3` | 语义化版本发布 |
| `sha-{commit}` | 按 commit SHA 追踪 |

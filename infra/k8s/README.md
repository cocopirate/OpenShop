# Kubernetes 部署

## 环境

| 环境 | 命名空间 | 说明 |
|------|----------|------|
| 开发 | `openshop-dev` | 本地联调 |
| 测试 | `openshop-test` | QA 测试 |
| 生产 | `openshop-prod` | 正式环境 |

## 目录结构

```
k8s/
├── base/           # 通用基础配置
├── overlays/
│   ├── dev/
│   ├── test/
│   └── prod/
└── README.md
```

## 部署命令

```bash
kubectl apply -k infra/k8s/overlays/prod
```
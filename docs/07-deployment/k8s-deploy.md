# Kubernetes 部署

## 部署工具

项目使用 **Kustomize** 管理多环境配置，无需额外安装工具（kubectl 1.14+ 内置）。

## 目录结构

```
infra/k8s/
├── base/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   └── {service}/
│       ├── deployment.yaml
│       └── service.yaml
└── overlays/
    ├── dev/
    │   └── kustomization.yaml
    └── prod/
        └── kustomization.yaml
```

## 部署命令

```bash
# 部署到生产环境
kubectl apply -k infra/k8s/overlays/prod

# 部署到开发环境
kubectl apply -k infra/k8s/overlays/dev

# 查看 Kustomize 渲染结果（不实际部署）
kubectl kustomize infra/k8s/overlays/prod
```

## 查看部署状态

```bash
# 查看所有 Pod 状态
kubectl get pods -n openshop

# 查看某个服务的日志
kubectl logs -f deployment/consumer-service -n openshop

# 查看事件
kubectl get events -n openshop --sort-by='.lastTimestamp'
```

## 滚动更新

```bash
# 触发滚动更新（更新镜像版本）
kubectl set image deployment/consumer-service \
  consumer-service=openshop/consumer-service:v1.2.0 \
  -n openshop

# 查看更新进度
kubectl rollout status deployment/consumer-service -n openshop

# 回滚
kubectl rollout undo deployment/consumer-service -n openshop
```

## ConfigMap 和 Secret

```bash
# 查看 ConfigMap
kubectl get configmap -n openshop

# 更新 Secret（Base64 编码）
kubectl create secret generic openshop-secrets \
  --from-literal=SECRET_KEY=your-secret \
  --from-literal=DATABASE_URL=postgresql+asyncpg://... \
  -n openshop --dry-run=client -o yaml | kubectl apply -f -
```

## 健康检查

每个服务的 Deployment 配置了 `livenessProbe` 和 `readinessProbe`，指向 `/health` 端点：

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8001
  initialDelaySeconds: 15
  periodSeconds: 10
readinessProbe:
  httpGet:
    path: /health
    port: 8001
  initialDelaySeconds: 5
  periodSeconds: 5
```

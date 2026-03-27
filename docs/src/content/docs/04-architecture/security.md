---
title: 安全设计
---

## RBAC 权限模型

```
AdminUser ──┐
        ├──(admin_user_roles)──▶ Role ──(role_permissions)──▶ Permission
        └── status (active/disabled)
```

## JWT 安全

- **签名算法**：HS256，密钥通过环境变量 `SECRET_KEY` 注入，不硬编码
- **Token 有效期**：默认 30 分钟
- **拒绝 `none` 算法**：防止算法降级攻击
- **传输方式**：仅通过 `Authorization: Bearer` Header，不放 URL 参数

## Redis 实时控制

JWT 本身是无状态的，为实现实时权限撤销，使用 Redis 补充控制：

| Key 模式 | 类型 | 说明 |
|----------|------|------|
| `user_status:{uid}` | String | 账号状态：`active` 或 `disabled` |
| `user_perm_ver:{uid}` | String | 权限版本计数器 |
| `user_permissions:{uid}` | String (JSON) | 权限列表缓存，TTL 300s |

**鉴权校验伪代码：**

```python
async def auth_check(request, token):
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    uid = payload["uid"]

    # 1. 检查用户状态（实时）
    status = await redis.get(f"user_status:{uid}")
    if status == "disabled":
        raise HTTPException(401, "账号已禁用")

    # 2. 检查权限版本（实时）
    redis_ver = await redis.get(f"user_perm_ver:{uid}")
    if redis_ver and int(redis_ver) != payload["ver"]:
        raise HTTPException(401, "权限已变更，请重新登录")

    # 3. 检查路由权限
    required = f"{request.method}:{request.path}"
    if required not in payload["permissions"]:
        raise HTTPException(403, "无访问权限")
```

## 密码安全

- 使用 `passlib[bcrypt]` 哈希存储，cost factor 默认 12
- 登录接口使用恒定时间比较，防时序攻击
- 禁止在日志、响应体中输出明文或哈希密码

## 防权限提升

- 分配角色/权限接口校验操作者自身权限
- 普通管理员不能给自己分配超出自身角色范围的权限
- 删除角色时检查是否仍有用户绑定

## 隐私保护

- 手机号在日志中脱敏（`138****8000`）
- 数据库仅存储脱敏后的 `phone_masked` 用于查询
- 隐私号服务保护买卖双方真实手机号不被对方知晓

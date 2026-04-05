---
title: 认证服务 PRD
---

## 1. 背景与目标

认证服务（auth-service）是 OpenShop 微服务平台的统一身份认证中心，解决多端用户（管理员、消费者、商家）的登录鉴权问题。核心目标是：
- 为各端提供统一的登录入口，降低各服务自行管理认证逻辑的复杂性
- 通过 JWT 令牌机制实现无状态鉴权，支持分布式部署
- 通过 Token 版本号机制实现即时失效控制，保障安全性

## 2. 用户角色

| 角色 | 描述 |
|------|------|
| 管理员 | 通过后台登录，拥有系统管理权限，权限数据由 admin-service 提供 |
| 消费者 | 通过 App/小程序登录，使用手机号/密码或第三方授权 |
| 商家 | 商家主账号及子账号/员工账号登录 |
| 内部服务 | api-gateway、admin-bff、app-bff 等服务调用认证接口进行 Token 验证 |

## 3. 功能需求

### 3.1 核心功能

- 管理员登录：验证账号密码，从 admin-service 拉取权限数据，签发含权限的 JWT
- 消费者登录：验证手机号/密码，签发消费者 JWT
- 商家及子账号登录：验证商家/员工账号，签发商家 JWT
- 登出：将 Token 版本号递增，使当前用户所有已签发 Token 立即失效
- Token 刷新：在 Token 即将过期时，凭有效 Token 换取新 Token
- 消费者认证凭证注册：为新注册消费者创建登录凭证

### 3.2 功能详情

#### 管理员登录

- 输入：账号（用户名或邮箱）、密码
- 处理：验证账号密码 → 调用 admin-service 内部接口获取角色与权限列表 → 将权限集合写入 JWT payload → 签发 JWT
- 输出：`access_token`（JWT）、`token_type`、`expires_in`
- 边界：账号不存在或密码错误返回 401；admin-service 不可达时返回 503；账号被禁用返回 403

#### 消费者登录

- 输入：手机号、密码
- 处理：查询消费者认证凭证 → 校验密码 hash → 检查 Token 版本号 → 签发 JWT
- 输出：`access_token`、`token_type`、`expires_in`
- 边界：手机号未注册返回 404；密码错误连续 5 次锁定账号 15 分钟

#### 商家/子账号登录

- 输入：登录名、密码、角色类型（merchant/employee）
- 处理：查询商家账号或员工账号 → 校验密码 → 签发含商家 ID 的 JWT
- 输出：`access_token`、`token_type`、`expires_in`、`merchant_id`
- 边界：商家账号状态非 `approved` 时拒绝登录

#### 登出与 Token 失效控制

- 输入：有效的 Bearer Token
- 处理：从 Token 中解析用户 ID 和账号类型 → 将 Redis 中该用户的 `token_version` 递增
- 输出：204 No Content
- 机制：每次签发 JWT 时将当前 `token_version` 写入 payload；验证 Token 时比对 Redis 中最新版本号，不一致则拒绝

#### 消费者认证凭证注册

- 输入：消费者 ID、手机号、密码（明文）
- 处理：对密码进行 bcrypt hash → 在认证凭证表创建记录
- 输出：凭证创建成功响应
- 边界：手机号已存在时返回 409

## 4. 非功能需求

| 类别 | 要求 |
|------|------|
| 性能 | 登录接口 P99 响应时间 < 300ms；Token 验证（网关侧）< 10ms |
| 安全 | 密码使用 bcrypt 存储；JWT 使用 HS256 或 RS256；Secret Key 通过环境变量注入，禁止硬编码 |
| 可用性 | 99.9% 月可用性；admin-service 不可达时管理员登录降级返回错误，不影响消费者/商家登录 |
| 幂等性 | 登出操作天然幂等（版本号只增不减） |
| 限流 | 登录接口按 IP 限流，防止暴力破解 |

## 5. 约束与依赖

| 依赖 | 说明 |
|------|------|
| admin-service（:8012） | 获取管理员角色与权限数据，仅在管理员登录时调用 |
| Redis | 存储各用户的 `token_version`，实现即时失效 |
| PostgreSQL | 存储消费者认证凭证、商家账号密码 |
| JWT 标准（RFC 7519） | Token 格式与验证规范 |

主要约束：
- auth-service 不持有权限主数据，权限数据完全来源于 admin-service
- Token 有效期通过 `ACCESS_TOKEN_EXPIRE_MINUTES` 配置，默认 30 分钟
- 不提供 OAuth2 第三方授权（当前版本）

## 6. 相关文档

- [认证服务概览](overview.md)
- [认证服务 API 参考](api.md)
- [认证接口（API 参考）](../../03-api-reference/auth.md)
- [安全设计](../../04-architecture/security.md)

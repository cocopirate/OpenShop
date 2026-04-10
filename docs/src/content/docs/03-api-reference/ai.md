---
title: AI 服务 API
---

**Base URL（直连）**: `http://localhost:8021`  
**Base URL（经网关）**: `http://localhost:8080`（网关路由前缀：`/api/v1/ai` → ai-service）  
**描述**: 平台级 AI 能力统一出口，支持多 Provider（OpenAI、Qwen/阿里云百炼等）。

所有响应均遵循统一格式：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... },
  "request_id": "uuid"
}
```

---

## 认证规则

| 路径 | 认证要求 |
|------|---------|
| `/api/v1/ai/complete/**` | `Authorization: Bearer <access_token>` **且** `X-Service-Key: <caller-key>`（服务间调用专用） |
| `/api/v1/ai/templates/**` | `Authorization: Bearer <access_token>` |
| `/api/v1/ai/logs/**` | `Authorization: Bearer <access_token>` |
| `/health` | 无需认证 |

`X-Service-Key` 由各调用方服务在 ai-service `.env` 中通过 `SERVICE_KEY_<NAME>` 配置。

---

## 健康检查

### GET /health

检查服务及依赖（DB、Redis）状态，无需认证。

**响应示例（200 OK）**

```json
{
  "status": "ok",
  "db": "ok",
  "redis": "ok",
  "providers": { "openai": "ok" }
}
```

**响应示例（503 降级）**

```json
{
  "status": "degraded",
  "db": "error",
  "redis": "ok",
  "providers": { "openai": "ok" }
}
```

---

## 模型补全 `/api/v1/ai/complete`

### POST /api/v1/ai/complete/raw

直接传入 Prompt，调用指定 Provider 完成推理。

**需要认证 + X-Service-Key**

**请求体**

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `provider` | string | `"openai"` | Provider 名称：`openai` \| `qwen` |
| `model` | string | `"gpt-4o-mini"` | 模型名称，见下方参考表 |
| `system_prompt` | string | 必填 | 系统 Prompt |
| `user_prompt` | string | 必填 | 用户 Prompt |
| `temperature` | float | `0.7` | 生成温度，范围 `[0, 2]` |
| `max_tokens` | int | `1000` | 最大输出 token 数 |
| `response_format` | string | `"text"` | `"text"` \| `"json_object"` |
| `caller_service` | string | 必填 | 调用方服务标识，写入日志 |
| `caller_ref_id` | string\|null | `null` | 调用方业务 ID，写入日志 |
| `cache_ttl_seconds` | int | `3600` | 缓存 TTL（秒）；`0` 表示不缓存 |

**请求示例**

```http
POST /api/v1/ai/complete/raw HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
X-Service-Key: seo-service-key-xxx
Content-Type: application/json

{
  "provider": "qwen",
  "model": "qwen-plus",
  "system_prompt": "你是一个专业的 SEO 顾问。",
  "user_prompt": "为一家卖运动鞋的电商网站生成 5 个标题建议。",
  "temperature": 0.8,
  "max_tokens": 500,
  "caller_service": "seo-service",
  "caller_ref_id": "shop-123"
}
```

**响应示例（200 OK）**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "call_id": "d3f8a1b2-...",
    "content": "1. 跑出你的速度 ...",
    "usage": { "prompt_tokens": 62, "completion_tokens": 120, "total_tokens": 182 },
    "provider": "qwen",
    "model": "qwen-plus",
    "cache_hit": false,
    "duration_ms": 1240
  },
  "request_id": "uuid"
}
```

**错误响应**

| 状态码 | 错误码 | 说明 |
|--------|--------|------|
| 401 | 40009 | 缺少 X-Service-Key |
| 401 | 40010 | X-Service-Key 无效 |
| 404 | 42004 | Provider 不存在 |
| 422 | 40011 | 请求体校验失败 |
| 429 | 42005 | 触发限流 |
| 502 | 42006 | Provider 调用失败 |

---

### POST /api/v1/ai/complete/template

使用预存的 Prompt 模板完成推理，变量自动渲染。

**需要认证 + X-Service-Key**

**请求体**

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `template_key` | string | 必填 | 模板唯一标识 |
| `variables` | object | `{}` | 渲染模板所需的变量键值对 |
| `caller_service` | string | 必填 | 调用方服务标识 |
| `caller_ref_id` | string\|null | `null` | 调用方业务 ID |
| `cache_ttl_seconds` | int | `3600` | 缓存 TTL（秒） |

**请求示例**

```http
POST /api/v1/ai/complete/template HTTP/1.1
Host: localhost:8080
Authorization: Bearer <access_token>
X-Service-Key: seo-service-key-xxx
Content-Type: application/json

{
  "template_key": "seo.title_suggest",
  "variables": { "category": "运动鞋", "brand": "Nike" },
  "caller_service": "seo-service",
  "caller_ref_id": "product-456"
}
```

**响应体**：同 `POST /api/v1/ai/complete/raw`

**错误响应**

| 状态码 | 错误码 | 说明 |
|--------|--------|------|
| 404 | 42001 | 指定 `template_key` 无活跃版本 |
| 422 | 42003 | 模板变量缺失 |
| 429 | 42005 | 触发限流 |
| 502 | 42006 | Provider 调用失败 |

---

## 模板管理 `/api/v1/ai/templates`

### GET /api/v1/ai/templates

列出所有模板。

**需要认证**

**Query 参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `key` | string | 按 key 模糊过滤（可选） |

**响应示例（200 OK）**

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": 1,
      "key": "seo.title_suggest",
      "version": 2,
      "is_active": true,
      "provider": "qwen",
      "model": "qwen-plus",
      "system_prompt": "你是一个 SEO 顾问。",
      "user_prompt_template": "为 {category} 品牌 {brand} 生成 5 个标题。",
      "temperature": 0.8,
      "max_tokens": 500,
      "response_format": "text",
      "created_at": "2026-04-10T08:00:00Z",
      "updated_at": "2026-04-10T09:00:00Z"
    }
  ],
  "request_id": "uuid"
}
```

---

### GET /api/v1/ai/templates/{key}

获取指定 key 的当前活跃版本。

**需要认证**

**路径参数**

| 参数 | 说明 |
|------|------|
| `key` | 模板唯一标识 |

**错误响应**

| 状态码 | 错误码 | 说明 |
|--------|--------|------|
| 404 | 42001 | 无活跃版本 |

---

### GET /api/v1/ai/templates/{key}/versions

获取指定 key 的所有历史版本，按版本号降序排列。

**需要认证**

**错误响应**

| 状态码 | 错误码 | 说明 |
|--------|--------|------|
| 404 | 42001 | 该 key 不存在任何版本 |

---

### POST /api/v1/ai/templates

创建新模板（版本自动设为 1）。

**需要认证**

**请求体**

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `key` | string | 必填 | 模板唯一标识，全局唯一 |
| `provider` | string | `"openai"` | Provider 名称 |
| `model` | string\|null | `null` | 指定模型；`null` 则使用 Provider 默认模型 |
| `system_prompt` | string | 必填 | 系统 Prompt |
| `user_prompt_template` | string | 必填 | 用户 Prompt 模板，变量用 `{variable}` 占位 |
| `temperature` | float | `0.7` | 生成温度 |
| `max_tokens` | int | `1000` | 最大输出 token 数 |
| `response_format` | string | `"text"` | `"text"` \| `"json_object"` |

**响应**：状态码 `201`，body 为 `TemplateResponse`

**错误响应**

| 状态码 | 错误码 | 说明 |
|--------|--------|------|
| 409 | 42002 | key 已存在，应使用 `POST /templates/{key}/versions` |

---

### POST /api/v1/ai/templates/{key}/versions

为已有 key 新增版本，旧活跃版本自动停用。

**需要认证**；请求体同 `POST /api/v1/ai/templates`（`key` 字段忽略）

**错误响应**

| 状态码 | 错误码 | 说明 |
|--------|--------|------|
| 404 | 42001 | key 不存在 |

---

### PATCH /api/v1/ai/templates/{key}

就地更新当前活跃版本的部分字段（不新增版本）。

**需要认证**

**请求体**（所有字段可选）

| 字段 | 类型 | 说明 |
|------|------|------|
| `model` | string\|null | 更新模型 |
| `temperature` | float\|null | 更新温度 |
| `max_tokens` | int\|null | 更新最大 token 数 |
| `response_format` | string\|null | 更新输出格式 |

**错误响应**

| 状态码 | 错误码 | 说明 |
|--------|--------|------|
| 404 | 42001 | 无活跃版本 |

---

### POST /api/v1/ai/templates/{key}/rollback/{version}

将指定版本设为活跃版本，当前活跃版本自动停用。

**需要认证**

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `key` | string | 模板唯一标识 |
| `version` | int | 目标回滚版本号 |

**错误响应**

| 状态码 | 错误码 | 说明 |
|--------|--------|------|
| 404 | 42001 | 指定版本不存在 |

---

## 调用日志 `/api/v1/ai/logs`

### GET /api/v1/ai/logs

分页查询调用日志。

**需要认证**

**Query 参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `caller_service` | string | 按调用方服务过滤（可选） |
| `template_key` | string | 按模板 key 过滤（可选） |
| `status` | string | `success` \| `failed` \| `rate_limited`（可选） |
| `date_from` | datetime | 开始时间，ISO 8601（可选） |
| `date_to` | datetime | 结束时间，ISO 8601（可选） |
| `page` | int | 页码，默认 `1` |
| `page_size` | int | 每页条数，默认 `20`，最大 `100` |

**响应示例（200 OK）**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "d3f8a1b2-...",
        "caller_service": "seo-service",
        "caller_ref_id": "shop-123",
        "template_key": null,
        "template_version": null,
        "provider": "qwen",
        "model": "qwen-plus",
        "prompt_tokens": 62,
        "completion_tokens": 120,
        "total_tokens": 182,
        "estimated_cost_usd": 0.000193,
        "status": "success",
        "error_message": null,
        "duration_ms": 1240,
        "cache_hit": false,
        "created_at": "2026-04-10T08:30:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  },
  "request_id": "uuid"
}
```

---

### GET /api/v1/ai/logs/stats

按调用方服务和模板统计汇总数据。

**需要认证**

**Query 参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `date_from` | datetime | 统计开始时间（可选） |
| `date_to` | datetime | 统计结束时间（可选） |

**响应示例（200 OK）**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "period": "2026-04-01 ~ 2026-04-10",
    "by_service": [
      {
        "caller_service": "seo-service",
        "total_calls": 320,
        "success_rate": 0.9875,
        "total_tokens": 58240,
        "estimated_cost_usd": 0.0621,
        "avg_duration_ms": 1105.3
      }
    ],
    "by_template": [
      {
        "template_key": "seo.title_suggest",
        "total_calls": 180,
        "cache_hit_rate": 0.42
      }
    ]
  },
  "request_id": "uuid"
}
```

---

## Provider 与模型参考

### OpenAI

| 模型 | 说明 |
|------|------|
| `gpt-4o-mini` | 默认，性价比高 |
| `gpt-4o` | 高能力 |

### 阿里云百炼（Qwen）

| 模型 | 说明 |
|------|------|
| `qwen-turbo` | 极速，低成本 |
| `qwen-plus` | 默认，均衡 |
| `qwen-max` | 最高能力 |
| `qwen-long` | 超长上下文 |

> Qwen 使用阿里云百炼 OpenAI 兼容接口，Base URL：`https://dashscope.aliyuncs.com/compatible-mode/v1`

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| 42001 | 模板不存在或无活跃版本 |
| 42002 | 模板 key 已存在 |
| 42003 | 模板变量缺失 |
| 42004 | Provider 不存在 |
| 42005 | 触发限流 |
| 42006 | Provider 调用失败 |

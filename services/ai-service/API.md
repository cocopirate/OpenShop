# AI Service API 文档

**版本**: 1.0.0  
**Base URL**: `http://localhost:8021`  
**API 前缀**: `/api/v1`  
**描述**: 平台级 AI 能力统一出口，支持多 Provider（OpenAI、Qwen/阿里云百炼等）。

---

## 认证

除 `/health`、`/docs`、`/openapi.json`、`/redoc` 外，所有接口均需通过服务间认证。

| Header | 说明 |
|---|---|
| `X-Service-Key` | 调用方服务密钥，在 `.env` 中配置 `SERVICE_KEY_<NAME>` |
| `X-Request-ID` | 可选，请求追踪 ID；未传时服务自动生成并在响应头返回 |

认证失败响应：

```json
HTTP 401
{ "detail": "Missing X-Service-Key header" }
{ "detail": "Invalid service key" }
```

---

## 健康检查

### `GET /health`

> 无版本前缀，直接访问根路径。

检查服务及依赖（DB、Redis）状态，无需认证。

**响应示例（正常）**

```json
HTTP 200
{
  "status": "ok",
  "db": "ok",
  "redis": "ok",
  "providers": { "openai": "ok" }
}
```

**响应示例（降级）**

```json
HTTP 503
{
  "status": "degraded",
  "db": "error",
  "redis": "ok",
  "providers": { "openai": "ok" }
}
```

---

## 补全接口 `/api/v1/ai/complete`

### `POST /api/v1/ai/complete/raw`

直接传入 Prompt，调用指定 Provider 完成推理。

**请求体**

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `provider` | `string` | `"openai"` | Provider 名称：`openai` \| `qwen` \| `anthropic` |
| `model` | `string` | `"gpt-4o-mini"` | 模型名称，见各 Provider 支持列表 |
| `system_prompt` | `string` | 必填 | 系统 Prompt |
| `user_prompt` | `string` | 必填 | 用户 Prompt |
| `temperature` | `float` | `0.7` | 生成温度，范围 `[0, 2]` |
| `max_tokens` | `int` | `1000` | 最大输出 token 数 |
| `response_format` | `string` | `"text"` | `"text"` \| `"json_object"` |
| `caller_service` | `string` | 必填 | 调用方服务标识，写入日志 |
| `caller_ref_id` | `string \| null` | `null` | 调用方业务 ID，写入日志 |
| `cache_ttl_seconds` | `int` | `3600` | 缓存 TTL（秒）；`0` 表示不缓存 |

**请求示例**

```json
POST /api/v1/ai/complete/raw
X-Service-Key: seo-service-key-xxx

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

**响应体** `CompletionResponse`

| 字段 | 类型 | 说明 |
|---|---|---|
| `call_id` | `uuid` | 本次调用 ID |
| `content` | `any` | AI 返回内容；`json_object` 模式时为解析后的对象 |
| `usage.prompt_tokens` | `int` | 输入 token 数 |
| `usage.completion_tokens` | `int` | 输出 token 数 |
| `usage.total_tokens` | `int` | 合计 token 数 |
| `provider` | `string` | 实际使用的 Provider |
| `model` | `string` | 实际使用的模型 |
| `cache_hit` | `bool` | 是否命中缓存 |
| `duration_ms` | `int` | 本次请求耗时（毫秒） |

**响应示例**

```json
HTTP 200
{
  "call_id": "d3f8a1b2-...",
  "content": "1. 跑出你的速度 ...",
  "usage": { "prompt_tokens": 62, "completion_tokens": 120, "total_tokens": 182 },
  "provider": "qwen",
  "model": "qwen-plus",
  "cache_hit": false,
  "duration_ms": 1240
}
```

**错误响应**

| 状态码 | 场景 |
|---|---|
| `422` | 请求体校验失败 |
| `429` | 触发限流，`detail.retry_after` 为建议等待秒数 |
| `502` | Provider 调用失败 |

---

### `POST /api/v1/ai/complete/template`

使用预存的 Prompt 模板完成推理，变量自动渲染。

**请求体**

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `template_key` | `string` | 必填 | 模板唯一标识 |
| `variables` | `object` | `{}` | 渲染模板所需的变量键值对 |
| `caller_service` | `string` | 必填 | 调用方服务标识 |
| `caller_ref_id` | `string \| null` | `null` | 调用方业务 ID |
| `cache_ttl_seconds` | `int` | `3600` | 缓存 TTL（秒） |

**请求示例**

```json
POST /api/v1/ai/complete/template
X-Service-Key: seo-service-key-xxx

{
  "template_key": "seo.title_suggest",
  "variables": { "category": "运动鞋", "brand": "Nike" },
  "caller_service": "seo-service",
  "caller_ref_id": "product-456"
}
```

**响应体**：同 `POST /complete/raw`

**错误响应**

| 状态码 | 场景 |
|---|---|
| `404` | 指定 `template_key` 无活跃版本 |
| `422` | 模板变量缺失或请求体校验失败 |
| `429` | 触发限流 |
| `502` | Provider 调用失败 |

---

## 模板管理 `/api/v1/ai/templates`

### `GET /api/v1/ai/templates`

列出所有模板（所有版本）。

**Query 参数**

| 参数 | 类型 | 说明 |
|---|---|---|
| `key` | `string` | 按 key 模糊过滤（可选） |

**响应体** `TemplateResponse[]`

```json
HTTP 200
[
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
]
```

---

### `GET /api/v1/ai/templates/{key}`

获取指定 key 的当前活跃版本模板。

**路径参数**

| 参数 | 说明 |
|---|---|
| `key` | 模板唯一标识 |

**响应体**: `TemplateResponse`

**错误响应**

| 状态码 | 场景 |
|---|---|
| `404` | 无活跃版本 |

---

### `GET /api/v1/ai/templates/{key}/versions`

获取指定 key 的所有历史版本，按版本号降序排列。

**响应体**: `TemplateResponse[]`

**错误响应**

| 状态码 | 场景 |
|---|---|
| `404` | 该 key 不存在任何版本 |

---

### `POST /api/v1/ai/templates`

创建新模板（首次，版本自动设为 1）。

**请求体** `TemplateCreate`

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `key` | `string` | 必填 | 模板唯一标识，全局唯一 |
| `provider` | `string` | `"openai"` | Provider 名称 |
| `model` | `string \| null` | `null` | 指定模型；`null` 则使用 Provider 默认模型 |
| `system_prompt` | `string` | 必填 | 系统 Prompt |
| `user_prompt_template` | `string` | 必填 | 用户 Prompt 模板，变量用 `{variable}` 占位 |
| `temperature` | `float` | `0.7` | 生成温度 |
| `max_tokens` | `int` | `1000` | 最大输出 token 数 |
| `response_format` | `string` | `"text"` | `"text"` \| `"json_object"` |

**响应体**: `TemplateResponse`，状态码 `201`

**错误响应**

| 状态码 | 场景 |
|---|---|
| `409` | key 已存在，应使用 `POST /templates/{key}/versions` |

---

### `POST /api/v1/ai/templates/{key}/versions`

为已有 key 添加新版本，旧活跃版本自动停用。

**请求体**: 同 `TemplateCreate`（`key` 字段忽略，以路径参数为准）

**响应体**: `TemplateResponse`，状态码 `201`

**错误响应**

| 状态码 | 场景 |
|---|---|
| `404` | key 不存在 |

---

### `PATCH /api/v1/ai/templates/{key}`

更新当前活跃版本的部分字段（就地修改，不新增版本）。

**请求体** `TemplateUpdate`（所有字段可选）

| 字段 | 类型 | 说明 |
|---|---|---|
| `model` | `string \| null` | 更新模型 |
| `temperature` | `float \| null` | 更新温度 |
| `max_tokens` | `int \| null` | 更新最大 token 数 |
| `response_format` | `string \| null` | 更新输出格式 |

**响应体**: `TemplateResponse`

**错误响应**

| 状态码 | 场景 |
|---|---|
| `404` | 无活跃版本 |

---

### `POST /api/v1/ai/templates/{key}/rollback/{version}`

将指定版本设为活跃版本，当前活跃版本自动停用。

**路径参数**

| 参数 | 类型 | 说明 |
|---|---|---|
| `key` | `string` | 模板唯一标识 |
| `version` | `int` | 目标回滚版本号 |

**响应体**: `TemplateResponse`

**错误响应**

| 状态码 | 场景 |
|---|---|
| `404` | 指定版本不存在 |

---

## 调用日志 `/api/v1/ai/logs`

### `GET /api/v1/ai/logs`

分页查询调用日志。

**Query 参数**

| 参数 | 类型 | 说明 |
|---|---|---|
| `caller_service` | `string` | 按调用方服务过滤（可选） |
| `template_key` | `string` | 按模板 key 过滤（可选） |
| `status` | `string` | 按状态过滤：`success` \| `failed` \| `rate_limited`（可选） |
| `date_from` | `datetime` | 开始时间（ISO 8601，可选） |
| `date_to` | `datetime` | 结束时间（ISO 8601，可选） |
| `page` | `int` | 页码，默认 `1` |
| `page_size` | `int` | 每页条数，默认 `20`，最大 `100` |

**响应体** `CallLogListResponse`

```json
HTTP 200
{
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
      "request_hash": "a3f1...",
      "cache_hit": false,
      "created_at": "2026-04-10T08:30:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

---

### `GET /api/v1/ai/logs/stats`

按调用方服务和模板统计汇总数据。

**Query 参数**

| 参数 | 类型 | 说明 |
|---|---|---|
| `date_from` | `datetime` | 统计开始时间（ISO 8601，可选） |
| `date_to` | `datetime` | 统计结束时间（ISO 8601，可选） |

**响应体** `LogStatsResponse`

```json
HTTP 200
{
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
}
```

---

## Provider 与模型参考

### OpenAI

| 模型 | 说明 |
|---|---|
| `gpt-4o-mini` | 默认，性价比高 |
| `gpt-4o` | 高能力 |

### 阿里云百炼（Qwen）

| 模型 | 说明 |
|---|---|
| `qwen-turbo` | 极速，低成本 |
| `qwen-plus` | 默认，均衡 |
| `qwen-max` | 最高能力 |
| `qwen-long` | 超长上下文 |

> Provider `qwen` 对应阿里云百炼平台 OpenAI 兼容接口，Base URL：`https://dashscope.aliyuncs.com/compatible-mode/v1`

---

## 错误格式

所有错误统一结构：

```json
{ "detail": "<错误描述>" }
```

限流错误（429）包含额外字段：

```json
{ "detail": { "error": "rate_limited", "retry_after": 12 } }
```

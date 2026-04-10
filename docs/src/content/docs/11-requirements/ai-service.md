---
title: AI Service 需求文档
---

## 0. 背景与定位

### 为什么要有 AI Service

平台多个业务服务（SEO 内容生成、客服回复、商品描述等）都需要调用大模型。如果各服务自己持有 API Key、自己处理重试和限流，会带来：

- API Key 分散，费用无法统一追踪
- 各服务重复实现重试、超时、降级逻辑
- 模型切换时需要修改多个服务
- 无法统一审计 Prompt 内容和输出质量

AI Service 解决上述问题，对内提供统一的 AI 调用接口。

### 服务边界

**AI Service 负责**：

- 持有并管理所有 AI 提供商的 API Key
- 接收业务服务的调用请求，转发给 AI 提供商
- 统一处理重试、超时、限流、降级
- 记录每次调用的日志（输入、输出、耗时、费用估算）
- 管理 Prompt 模板（集中维护，版本化）

**AI Service 不负责**：

- 理解业务语义（不关心"这是在生成 SEO 内容"还是"在回复客服"）
- 持久化业务数据（结果由调用方自己存储）
- 用户认证（由 Gateway 处理，本服务只做服务间调用）

---

## 1. 技术栈

| 层 | 选型 | 说明 |
|---|---|---|
| Web 框架 | **FastAPI** | 原生异步，适合 IO 密集型 AI 调用 |
| 数据库 | **PostgreSQL 15**（独立实例） | 存储调用日志、Prompt 模板 |
| ORM + 迁移 | **SQLAlchemy 2.x + Alembic** | |
| 缓存 | **Redis 7** | 限流计数器、相同 Prompt 结果缓存 |
| AI SDK | **OpenAI Python SDK v1.x** | 首选提供商 |
| HTTP 客户端 | **httpx** | 对接其他 AI 提供商备用 |
| 容器化 | **Docker + Docker Compose** | |
| 配置管理 | **pydantic-settings** | |

---

## 2. 项目结构

```
ai-service/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   │   ├── call_log.py          # 调用日志
│   │   └── prompt_template.py   # Prompt 模板
│   ├── schemas/                 # Pydantic request/response
│   ├── routers/
│   │   ├── complete.py          # 核心补全接口
│   │   ├── templates.py         # Prompt 模板管理
│   │   └── logs.py              # 调用日志查询
│   ├── services/
│   │   ├── providers/
│   │   │   ├── base.py          # Provider 抽象基类
│   │   │   ├── openai.py        # OpenAI 实现
│   │   │   └── anthropic.py     # Anthropic 实现（预留骨架）
│   │   ├── router.py            # Provider 路由选择逻辑
│   │   ├── rate_limiter.py      # 限流
│   │   └── cache.py             # 结果缓存
│   └── middleware/
│       └── auth.py              # 服务间调用鉴权
├── alembic/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## 3. 数据库设计

### 3.1 prompt_template（Prompt 模板）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | SERIAL PK | |
| key | VARCHAR NOT NULL | 业务标识，如 `seo.page.generate`、`cs.reply.suggest` |
| version | INTEGER DEFAULT 1 | 同一 key 可有多个版本 |
| is_active | BOOLEAN DEFAULT true | 同一 key 只有一个版本 is_active=true |
| provider | VARCHAR DEFAULT 'openai' | 绑定的提供商 |
| model | VARCHAR | 如 `gpt-4o-mini`，空则用全局默认 |
| system_prompt | TEXT NOT NULL | System message 内容 |
| user_prompt_template | TEXT NOT NULL | User message 模板，用 `{variable}` 占位 |
| temperature | FLOAT DEFAULT 0.7 | |
| max_tokens | INTEGER DEFAULT 1000 | |
| response_format | VARCHAR DEFAULT 'text' | `text` / `json_object` |
| created_at | TIMESTAMPTZ DEFAULT now() | |
| updated_at | TIMESTAMPTZ DEFAULT now() | |

**唯一约束**：`UNIQUE(key, version)`

**说明**：调用方通过 `template_key` 引用模板，AI Service 自动取当前 active 版本。更新模板时递增 version，旧版本 is_active 改为 false，保留历史可回滚。

### 3.2 call_log（调用日志）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID PK DEFAULT gen_random_uuid() | |
| caller_service | VARCHAR NOT NULL | 调用方服务名，如 `seo-service` |
| caller_ref_id | VARCHAR | 调用方自定义业务 ID，用于关联溯源 |
| template_key | VARCHAR | 使用的模板 key，直接调用时为 null |
| template_version | INTEGER | 使用的模板版本号 |
| provider | VARCHAR NOT NULL | 实际使用的提供商 |
| model | VARCHAR NOT NULL | 实际使用的模型 |
| prompt_tokens | INTEGER | 输入 token 数 |
| completion_tokens | INTEGER | 输出 token 数 |
| total_tokens | INTEGER | 合计 |
| estimated_cost_usd | NUMERIC(10,6) | 估算费用（美元） |
| status | VARCHAR | `success` / `failed` / `rate_limited` |
| error_message | TEXT | 失败时的错误信息 |
| duration_ms | INTEGER | 调用耗时（毫秒） |
| request_hash | VARCHAR | 请求内容的 hash，用于缓存命中检测 |
| cache_hit | BOOLEAN DEFAULT false | 是否命中缓存 |
| created_at | TIMESTAMPTZ DEFAULT now() | |

> **注意**：call_log **不存储** prompt 原文和 AI 输出内容，只存元数据，防止敏感信息落库。完整内容审计（存 S3）作为后续扩展，当前版本不实现。

---

## 4. 接口设计

### 4.1 健康检查

```
GET /health
```

```json
{
  "status": "ok",
  "db": "ok",
  "redis": "ok",
  "providers": {
    "openai": "ok"
  }
}
```

---

### 4.2 核心：基于模板的补全（推荐）

```
POST /complete/template
```

调用方传入模板 key 和变量，AI Service 渲染模板后调用 AI，调用方完全不感知 prompt 细节。

**请求体**：

```json
{
  "template_key": "seo.page.generate",
  "variables": {
    "city_name": "上海",
    "district_name": "浦东",
    "service_name": "MacBook维修",
    "service_description": "MacBook各种硬件软件故障维修",
    "base_price": "300",
    "landmarks": "陆家嘴, 金茂大厦",
    "keywords": "MacBook维修, 苹果笔记本维修"
  },
  "caller_service": "seo-service",
  "caller_ref_id": "job_uuid_xxx",
  "cache_ttl_seconds": 3600
}
```

**响应**：

```json
{
  "call_id": "uuid",
  "content": { },
  "usage": {
    "prompt_tokens": 320,
    "completion_tokens": 480,
    "total_tokens": 800
  },
  "provider": "openai",
  "model": "gpt-4o-mini",
  "cache_hit": false,
  "duration_ms": 1240
}
```

- `content` 类型：若模板 `response_format=json_object`，返回 JSON 对象；否则返回字符串
- `cache_ttl_seconds=0` 表示本次不缓存
- 模板不存在或无 active 版本，返回 404

---

### 4.3 核心：自由调用（不使用模板）

```
POST /complete/raw
```

调用方自己传入完整 prompt，适用于高度动态或临时调试场景。

**请求体**：

```json
{
  "provider": "openai",
  "model": "gpt-4o-mini",
  "system_prompt": "你是...",
  "user_prompt": "请帮我...",
  "temperature": 0.7,
  "max_tokens": 1000,
  "response_format": "json_object",
  "caller_service": "cs-service",
  "caller_ref_id": "ticket_456",
  "cache_ttl_seconds": 0
}
```

**响应**：同 `/complete/template`

---

### 4.4 Prompt 模板管理

| Method | Path | 功能 |
|---|---|---|
| GET | `/templates` | 模板列表，支持按 key 搜索 |
| GET | `/templates/{key}` | 获取指定 key 的当前 active 版本 |
| GET | `/templates/{key}/versions` | 获取指定 key 的所有历史版本 |
| POST | `/templates` | 新建模板（首版 version=1） |
| POST | `/templates/{key}/versions` | 新增版本（自动 version+1，旧版 is_active→false） |
| PATCH | `/templates/{key}` | 修改当前版本的 temperature 等非 prompt 字段 |
| POST | `/templates/{key}/rollback/{version}` | 回滚到指定版本（将其设为 active） |

---

### 4.5 调用日志查询

```
GET /logs
```

Query 参数：`caller_service`, `template_key`, `status`, `date_from`, `date_to`, `page`, `page_size`

```
GET /logs/stats
```

返回指定时间范围的汇总统计：

```json
{
  "period": "2024-01-01 ~ 2024-01-31",
  "by_service": [
    {
      "caller_service": "seo-service",
      "total_calls": 1240,
      "success_rate": 0.98,
      "total_tokens": 892000,
      "estimated_cost_usd": 1.34,
      "avg_duration_ms": 1180
    }
  ],
  "by_template": [
    {
      "template_key": "seo.page.generate",
      "total_calls": 980,
      "cache_hit_rate": 0.12
    }
  ]
}
```

---

## 5. 核心机制

### 5.1 服务间鉴权

调用方在请求 Header 中携带服务专属 API Key：

```
X-Service-Key: seo-service-key-xxx
```

- 每个业务服务分配独立的 Service Key，在 AI Service 环境变量中配置
- Key 无效直接返回 401，不记录 call_log
- 当前版本用静态 Key，后续可升级为动态 Key 管理

### 5.2 限流

基于 Redis 计数器，按 `caller_service` 维度双重限流：

| 维度 | 默认限制 | 说明 |
|---|---|---|
| 每分钟请求数（RPM） | 60次 / 服务 | 可通过环境变量按服务单独配置 |
| 每分钟 Token 数（TPM） | 100,000 / 服务 | 防止单服务消耗过多配额 |

超限返回 `429`，响应体：

```json
{
  "error": "rate_limited",
  "retry_after": 23
}
```

### 5.3 结果缓存

对完全相同的请求（system_prompt + user_prompt hash 一致）缓存返回结果：

- 缓存存储：Redis，Key 为 `cache:{request_hash}`
- 默认 TTL：**1小时**，可通过请求参数 `cache_ttl_seconds` 覆盖
- `cache_ttl_seconds=0` 表示本次强制跳过缓存
- 命中缓存时直接返回，不调用 AI，call_log 记录 `cache_hit=true`

### 5.4 重试与超时

| 参数 | 默认值 | 说明 |
|---|---|---|
| 单次请求超时 | 30秒 | |
| 自动重试次数 | 2次 | 仅对网络错误和 5xx 重试，4xx 不重试 |
| 重试间隔 | 指数退避：1s / 2s | |

重试在 AI Service 内部透明处理，调用方只感知最终结果。

### 5.5 Provider 抽象

所有 AI 提供商实现统一的抽象基类：

```python
# services/providers/base.py
class BaseProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        response_format: str,
    ) -> CompletionResult:
        pass
```

当前实现 `OpenAIProvider`，预留 `AnthropicProvider` 骨架。新增提供商只需实现该基类，调用方和模板层零改动。

---

## 6. 调用方对接方式（以 SEO Service 为例）

SEO Service 不再直接调用 OpenAI，改为调用 AI Service：

```python
# seo-service 中 ai_generator.py
import httpx
from app.config import settings

async def call_ai_template(template_key: str, variables: dict, ref_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.AI_SERVICE_URL}/complete/template",
            headers={"X-Service-Key": settings.AI_SERVICE_KEY},
            json={
                "template_key": template_key,
                "variables": variables,
                "caller_service": "seo-service",
                "caller_ref_id": ref_id,
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json()["content"]
```

SEO Service 侧新增环境变量：

```env
AI_SERVICE_URL=http://ai-service:8001
AI_SERVICE_KEY=seo-service-key-xxx
```

SEO Service **移除** `OPENAI_API_KEY`。

---

## 7. 环境变量

```env
# 数据库（独立实例）
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/ai_service_db

# Redis
REDIS_URL=redis://localhost:6379/0

# AI 提供商
OPENAI_API_KEY=sk-...
OPENAI_DEFAULT_MODEL=gpt-4o-mini

# 服务间鉴权（每个调用方服务一个 Key）
SERVICE_KEY_SEO=seo-service-key-xxx
SERVICE_KEY_CS=cs-service-key-xxx

# 限流默认值（可按服务覆盖）
RATE_LIMIT_RPM=60
RATE_LIMIT_TPM=100000

# 缓存
CACHE_DEFAULT_TTL=3600
```

---

## 8. Docker Compose 结构

```yaml
services:
  ai_postgres:
    image: postgres:15

  ai_redis:
    image: redis:7-alpine

  ai_api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    ports: ["8001:8000"]    # 对外暴露 8001，避免与其他服务冲突
    depends_on: [ai_postgres, ai_redis]
    environment:
      - DATABASE_URL
      - REDIS_URL
      - OPENAI_API_KEY
      - SERVICE_KEY_SEO
      - SERVICE_KEY_CS
```

---

## 9. 实现优先级

| 优先级 | 模块 | 完成标志 |
|---|---|---|
| P0 | 数据库模型 + Alembic 初始迁移 | 两张表建好 |
| P0 | OpenAI Provider 封装（含重试/超时） | 可发出请求并返回结果 |
| P0 | `POST /complete/raw` 接口 | SEO Service 可联调 |
| P0 | call_log 写入 | 每次调用有元数据记录 |
| P0 | 服务间 API Key 鉴权中间件 | 无效 Key 返回 401 |
| P1 | Prompt 模板表 + CRUD 接口 | SEO Service 切换为模板调用 |
| P1 | `POST /complete/template` 接口 | 调用方解耦 prompt 内容 |
| P1 | Redis 限流（RPM + TPM） | 防止单服务打爆配额 |
| P2 | 结果缓存（Redis） | 降低重复调用费用 |
| P2 | `GET /logs/stats` 统计接口 | 费用和调用情况可见 |
| P2 | 模板版本管理 + 回滚接口 | Prompt 迭代可追溯 |
| P3 | Anthropic Provider 骨架 | 多提供商扩展准备 |

---

## 10. 服务调用全景图

```
┌─────────────┐      ┌─────────────┐
│  SEO Service│      │  CS Service │  （其他业务服务）
└──────┬──────┘      └──────┬──────┘
       │ X-Service-Key       │ X-Service-Key
       │ POST /complete/...  │
       └──────────┬──────────┘
                  ▼
         ┌────────────────┐
         │   AI Service   │
         │                │
         │  ┌──────────┐  │
         │  │Rate Limit│  │──► Redis
         │  └──────────┘  │
         │  ┌──────────┐  │
         │  │  Cache   │  │──► Redis
         │  └──────────┘  │
         │  ┌──────────┐  │
         │  │call_log  │  │──► PostgreSQL（独立）
         │  └──────────┘  │
         └────────┬───────┘
                  │
          ┌───────┴────────┐
          ▼                ▼
     OpenAI API      Anthropic API
                     （预留，未实现）
```

---

## 11. 后续扩展（当前版本不实现）

- **流式响应**：`POST /complete/stream`，SSE 方式返回，适合实时打字效果
- **完整内容审计**：prompt 和输出加密后异步写入 S3，满足合规要求
- **动态限流配置**：通过管理接口动态调整各服务 RPM/TPM，无需重启
- **费用预警**：日费用超阈值时触发告警通知
- **A/B 测试**：同一 template_key 下多版本按比例分流，评估 prompt 效果
- **Embedding 接口**：`POST /embed`，统一提供向量化能力，供语义搜索等场景使用

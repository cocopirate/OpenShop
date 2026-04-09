---
title: SEO内容生成服务数据模型
---

## 数据库设计

### city（城市）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | 自增主键 |
| slug | VARCHAR UNIQUE NOT NULL | 全局唯一，如 `shanghai` |
| name | VARCHAR NOT NULL | 显示名，如 `上海` |
| pinyin | VARCHAR | 拼音，用于 URL |
| is_active | BOOLEAN DEFAULT true | 软删除标志 |
| created_at | TIMESTAMPTZ DEFAULT now() | 创建时间 |

### district（区）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | 自增主键 |
| city_id | INTEGER FK → city.id | 所属城市 |
| slug | VARCHAR NOT NULL | 区级别唯一（UNIQUE city_id + slug） |
| name | VARCHAR NOT NULL | 区名 |
| landmarks | JSONB DEFAULT '[]' | 地标列表，用于 AI Prompt |
| is_active | BOOLEAN DEFAULT true | 软删除标志 |
| created_at | TIMESTAMPTZ DEFAULT now() | 创建时间 |

**唯一约束**：`UNIQUE(city_id, slug)`

### service（服务类型）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | 自增主键 |
| slug | VARCHAR UNIQUE NOT NULL | 如 `macbook-repair` |
| name | VARCHAR NOT NULL | 如 `MacBook维修` |
| keywords | JSONB DEFAULT '[]' | SEO 关键词列表 |
| base_price | INTEGER | 参考价格（分） |
| description | TEXT | 服务描述，注入 Prompt |
| is_active | BOOLEAN DEFAULT true | 软删除标志 |
| created_at | TIMESTAMPTZ DEFAULT now() | 创建时间 |

### seo_page（SEO 页面）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | 自增主键 |
| city_id | INTEGER FK → city.id | 所属城市 |
| district_id | INTEGER FK → district.id | 所属区 |
| service_id | INTEGER FK → service.id | 所属服务类型 |
| slug | VARCHAR UNIQUE NOT NULL | 如 `shanghai/pudong/macbook-repair` |
| title | VARCHAR | `<title>` 标签内容 |
| meta_description | TEXT | `<meta description>` |
| h1 | VARCHAR | 页面 H1 |
| content | JSONB | AI 生成的结构化内容 |
| status | VARCHAR DEFAULT 'draft' | `draft` / `published` / `needs_review` |
| generation_count | INTEGER DEFAULT 0 | 累计生成次数 |
| created_at | TIMESTAMPTZ DEFAULT now() | 创建时间 |
| updated_at | TIMESTAMPTZ DEFAULT now() | 更新时间（自动刷新） |

**唯一约束**：`UNIQUE(city_id, district_id, service_id)` 和 `UNIQUE(slug)`

### generation_job（生成任务）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 任务ID |
| type | VARCHAR | `single` / `batch` |
| status | VARCHAR DEFAULT 'pending' | `pending` / `running` / `done` / `failed` |
| payload | JSONB | 触发参数 |
| result | JSONB | 统计摘要（total/created/skipped/failed） |
| error_log | JSONB DEFAULT '[]' | 失败条目的错误信息列表 |
| created_at | TIMESTAMPTZ DEFAULT now() | 创建时间 |
| finished_at | TIMESTAMPTZ | 完成时间 |

## AI 生成内容结构

```json
{
  "intro": "150字以内的服务介绍，自然融入城市/区名",
  "local_intro": "100字以内，结合地标描述服务覆盖范围",
  "service_items": [
    {"name": "服务项目名", "desc": "一句话描述", "price_hint": "价格参考"}
  ],
  "cases": [
    {"title": "案例标题", "desc": "案例描述，80字以内"}
  ],
  "faq": [
    {"q": "常见问题", "a": "回答，60字以内"}
  ],
  "cta": "行动号召文案，30字以内"
}
```

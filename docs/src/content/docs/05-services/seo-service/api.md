---
title: SEO内容生成服务 API
---

## 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查，返回 db 和 redis 状态 |

**响应示例**：
```json
{"status": "ok", "db": "ok", "redis": "ok"}
```

---

## SEO 页面查询

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/pages` | 列表查询，支持 city_slug / service_slug / status 过滤 |
| GET | `/pages/{slug}` | 获取单页，slug 格式：`shanghai/pudong/macbook-repair` |
| PATCH | `/pages/{slug}` | 更新页面字段（status / title / meta_description / h1） |

**Query 参数**（`GET /pages`）：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| city_slug | string | - | 按城市过滤 |
| service_slug | string | - | 按服务过滤 |
| status | string | - | 按状态过滤（draft/published/needs_review） |
| page | int | 1 | 页码 |
| page_size | int | 20 | 每页数量（最大100） |

---

## 生成接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/generate` | 触发单页生成，立即返回 job_id |
| POST | `/generate/batch` | 触发批量生成，立即返回 job_id |
| GET | `/generate/jobs/{job_id}` | 查询任务状态 |

**单页生成请求体**：
```json
{
  "city_slug": "shanghai",
  "district_slug": "pudong",
  "service_slug": "macbook-repair",
  "force": false
}
```

**批量生成请求体**：
```json
{
  "city_slugs": ["shanghai", "beijing"],
  "force": false
}
```

`city_slugs` 为空数组时，遍历所有 `is_active=true` 的城市。

**任务状态响应**：
```json
{
  "job_id": "uuid",
  "type": "batch",
  "status": "running",
  "result": {
    "total": 120,
    "created": 45,
    "skipped": 10,
    "failed": 2
  },
  "error_log": [
    {"slug": "beijing/chaoyang/macbook-repair", "error": "AI timeout"}
  ]
}
```

---

## 基础数据管理（Admin）

### 城市管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/cities` | 城市列表 |
| POST | `/admin/cities` | 新增城市 |
| PATCH | `/admin/cities/{slug}` | 更新城市（含 is_active） |

### 区管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/districts` | 区列表 |
| POST | `/admin/districts` | 新增区 |
| PATCH | `/admin/districts/{id}` | 更新区（含 landmarks） |

### 服务类型管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/services` | 服务列表 |
| POST | `/admin/services` | 新增服务 |
| PATCH | `/admin/services/{slug}` | 更新服务 |

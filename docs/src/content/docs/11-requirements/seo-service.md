---
title: SEO内容生成服务 PRD
---

## 1. 背景与目标

seo-service 是 OpenShop 平台的独立 SEO 内容生成微服务，解决以下问题：

- 为本地化服务页面批量生成高质量 SEO 内容，提升自然搜索流量
- 提供城市/区/服务三张维度表的统一管理
- 通过异步任务架构（ARQ + Redis）支持大批量内容生成，不阻塞主流程
- 内置重复检测，保证生成内容的多样性

## 2. 用户角色

| 角色 | 描述 |
|------|------|
| 平台运营 | 通过 Admin 接口管理城市、区、服务基础数据；触发批量生成 |
| 前端服务（Next.js） | 调用 `/pages` 接口消费 SEO 页面内容 |
| 内部监控 | 通过 `/health` 和 `/generate/jobs/{job_id}` 监控服务和任务状态 |

## 3. 功能需求

### 3.1 基础数据管理

- 城市管理：新增/更新城市，支持软删除（is_active）
- 区管理：新增/更新区，含地标列表（用于 AI Prompt 本地化）
- 服务类型管理：新增/更新服务，含关键词列表和参考价格

### 3.2 SEO 页面生成

- 单页生成：指定城市/区/服务组合，调用 OpenAI 生成内容，异步执行
- 批量生成：指定城市列表（或全量），遍历所有区×服务组合批量生成
- 强制重新生成：`force=true` 时覆盖已有内容，`generation_count + 1`
- 去重检测：对同服务类型的页面进行相似度检测，超阈值则重新生成

### 3.3 页面状态管理

| 状态 | 说明 |
|------|------|
| draft | 草稿，刚生成未发布 |
| published | 已发布，前端可消费 |
| needs_review | 重复检测失败或 AI 多次超时，需人工审核 |

### 3.4 任务追踪

- 每次生成触发创建 `GenerationJob` 记录
- Worker 实时更新任务进度（total/created/skipped/failed）
- 失败条目记录到 `error_log`，不阻断其他页面生成

## 4. 非功能需求

| 类别 | 要求 |
|------|------|
| 性能 | 单次 AI 调用超时重试1次；批量生成不影响 API 响应 |
| 可用性 | Redis/DB 不可用时 `/health` 返回 503 |
| 内容质量 | 重复相似度阈值 0.75（可配置），最多重试 3 次（可配置） |
| 独立性 | 不依赖 Gateway 和 User Service，独立部署 |

## 5. 约束与依赖

| 依赖 | 说明 |
|------|------|
| PostgreSQL 15 | 独立实例（DB per service 原则） |
| Redis 7 | ARQ broker，仅本服务使用 |
| OpenAI API | gpt-4o-mini，`response_format: json_object` |

主要约束：

- 所有 schema 变更必须通过 Alembic migration 管理，禁止 `create_all()`
- 端口 8020
- 数据模型详见 [数据模型文档](../05-services/seo-service/schema.md)

## 6. 相关文档

- [SEO服务概览](../05-services/seo-service/overview.md)
- [SEO服务 API 参考](../05-services/seo-service/api.md)
- [SEO服务数据模型](../05-services/seo-service/schema.md)

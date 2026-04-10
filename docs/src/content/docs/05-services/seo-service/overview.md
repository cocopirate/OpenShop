---
title: SEO内容生成服务
---

## 概述

seo-service（:8020）是一个独立微服务，负责管理本地化SEO页面的完整生命周期：

- 管理城市 / 区 / 服务三张维度表（基础数据）
- 异步批量调用 AI（OpenAI gpt-4o-mini），生成本地化SEO页面内容
- 管理SEO页面的生命周期（草稿 → 发布 → 重新生成）

本服务独立部署，不依赖 Gateway 和 User Service，通过 HTTP 对其他服务暴露接口。

## 端口

| 环境 | 端口 |
|------|------|
| 本地开发 | 8020 |
| Docker Compose | `seo_api:8020` |

## API Swagger UI

本地开发：http://localhost:8020/docs

## 相关文档

- [API 参考](api.md)
- [数据模型](schema.md)
- [需求文档](prd.md)

# Admin BFF (Backend For Frontend)

面向运营管理后台的 BFF 服务，聚合管理侧所需接口，提供适配管理后台的数据视图。

## 技术选型

- **框架**: FastAPI (Python 3.11+)
- **HTTP 客户端**: httpx (异步)
- **权限校验**: RBAC（基于角色的访问控制）

## 职责

- 管理接口聚合：汇总商品、订单、用户、商家的管理视图
- 权限控制：仅允许管理员角色访问
- 数据统计：提供报表所需聚合数据
- 操作审计：记录管理员操作日志

## 主要接口

| 接口 | 功能 |
|------|------|
| `GET /admin/v1/dashboard` | 运营数据看板 |
| `GET /admin/v1/orders` | 订单管理列表 |
| `GET /admin/v1/merchants` | 商家管理列表 |
| `POST /admin/v1/products` | 商品上架 |
| `GET /admin/v1/reports/sales` | 销售报表 |

## 短信管理接口

短信相关的管理接口由 **sms-service** 直接暴露（`/api/v1/admin/sms/*`），
通过 API Gateway 的 RBAC 层进行鉴权后转发。

| 接口 | 功能 |
|------|------|
| `GET /api/v1/admin/sms/records` | 查询短信发送记录（手机号/时间/状态过滤 + 分页） |
| `DELETE /api/v1/admin/sms/records/{id}` | 删除指定短信发送记录 |
| `GET /api/v1/admin/sms/templates` | 查询短信模板列表 |
| `POST /api/v1/admin/sms/templates` | 创建短信模板 |
| `GET /api/v1/admin/sms/templates/{id}` | 获取短信模板详情 |
| `PUT /api/v1/admin/sms/templates/{id}` | 更新短信模板 |
| `DELETE /api/v1/admin/sms/templates/{id}` | 删除短信模板 |
| `GET /api/v1/admin/sms/config` | 查询短信服务运行时配置 |
| `PUT /api/v1/admin/sms/config` | 动态更新短信服务运行时配置 |

完整接口文档见 sms-service Swagger UI：http://localhost:8010/docs

## 端口

- 服务端口: **8091**

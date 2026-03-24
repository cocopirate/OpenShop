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

## 端口

- 服务端口: **8091**

# product-service（商品服务）

负责商品 SPU/SKU 管理、分类管理及基于 Elasticsearch 的商品搜索。

## 职责

- 商品 SPU/SKU 创建与管理
- 商品分类与标签管理
- 商品搜索（Elasticsearch）

## 主要接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `GET /api/v1/products` | GET | 商品列表/搜索 |
| `POST /api/v1/products` | POST | 创建商品 |
| `GET /api/v1/products/{product_id}` | GET | 获取商品详情 |

## 数据模型

- Product (SPU)
- SKU
- Category
- ProductImage

## 依赖服务

- inventory-service（库存查询）
- merchant-service（商家验证）

## 端口

- 服务端口: **8003**

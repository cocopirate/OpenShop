# inventory-service（库存服务）

负责商品库存管理、库存锁定与释放，支持超卖防护。

## 职责

- 库存初始化与调整
- 下单时库存锁定（乐观锁/Redis）
- 取消/退款时库存释放

## 主要接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `GET /api/v1/inventory/{sku_id}` | GET | 查询 SKU 库存 |
| `POST /api/v1/inventory/{sku_id}/lock` | POST | 锁定库存 |
| `POST /api/v1/inventory/{sku_id}/release` | POST | 释放库存 |

## 数据模型

- Inventory
- InventoryLock
- StockRecord

## 依赖服务

- order-service（通过 RabbitMQ 监听订单事件）

## 端口

- 服务端口: **8004**

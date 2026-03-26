# order-service（订单服务）

负责订单 CRUD 及订单状态流转（待支付 -> 已支付 -> 已发货 -> 已完成）。

## 职责

- 订单创建与持久化
- 订单状态流转管理
- 订单查询与历史记录

## 主要接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `POST /api/v1/orders` | POST | 创建订单 |
| `GET /api/v1/orders/{order_id}` | GET | 获取订单详情 |
| `GET /api/v1/orders` | GET | 查询订单列表 |

## 数据模型

- Order
- OrderItem
- OrderStatusLog

## 依赖服务

- inventory-service（库存扣减，RabbitMQ）
- notification-service（订单通知，RabbitMQ）

## 端口

- 服务端口: **8005**

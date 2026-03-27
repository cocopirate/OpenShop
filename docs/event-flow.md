# 事件流设计文档

## RabbitMQ Exchanges / Routing Keys

| Routing Key | 生产者 | 消费者 | 说明 |
|-------------|--------|--------|------|
| `order.created` | order-service | inventory-service, notification-service | 订单创建 |
| `order.paid` | order-service | inventory-service, promotion-service, notification-service | 订单支付成功 |
| `order.cancelled` | order-service | inventory-service, notification-service | 订单取消 |
| `order.shipped` | order-service | notification-service, virtual-number-service | 订单发货 |
| `order.completed` | order-service | promotion-service | 订单完成 |
| `inventory.locked` | inventory-service | order-orchestration | 库存锁定确认 |
| `inventory.lock_failed` | inventory-service | order-orchestration | 库存锁定失败 |
| `customer.registered` | consumer-service | notification-service | 客户注册 |
| `aftersale.approved` | aftersale-service | notification-service, order-service | 售后审核通过 |

## 下单事件流（Saga 模式）

```
Client
  |-- POST /api/v1/orchestration/checkout
  |
order-orchestration
  |-- HTTP POST -> promotion-service: /validate_coupon
  |   |-- 成功 -> 继续
  |   `-- 失败 -> 返回错误
  |
  |-- HTTP POST -> inventory-service: /lock
  |   |-- 成功 -> 继续
  |   `-- 失败 -> 返回库存不足
  |
  |-- HTTP POST -> order-service: /orders
  |   |-- 成功 -> 发布 order.created
  |   `-- 失败 -> 补偿: inventory-service /release
  |
  `-- 返回 order_id 给客户端

order-service (RabbitMQ Consumer: order.created)
  `-- notification-service 收到事件 -> 发送下单成功通知
```

## 订单取消事件流

```
order.cancelled 事件
  |-- inventory-service: 释放锁定库存
  `-- notification-service: 发送取消通知
```

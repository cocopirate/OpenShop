---
title: Saga 编排模式
---

## 什么是 Saga？

Saga 是一种分布式事务模式，将一个长事务拆分为多个本地事务，每个本地事务成功后发布事件触发下一步，任意步骤失败时执行补偿操作（回滚）。

## 下单 Saga 流程

```
客户端 POST /api/v1/orchestration/checkout
    │
order-orchestration（Saga 编排器）
    │
    ├── Step 1: 校验优惠券
    │     HTTP POST → promotion-service: /validate_coupon
    │     ├── 成功 → 继续
    │     └── 失败 → 返回错误，结束
    │
    ├── Step 2: 锁定库存
    │     HTTP POST → inventory-service: /lock
    │     ├── 成功 → 继续
    │     └── 失败 → 返回库存不足，结束
    │
    ├── Step 3: 创建订单
    │     HTTP POST → order-service: /orders
    │     ├── 成功 → 发布 order.created
    │     └── 失败 → 补偿：inventory-service /release（释放库存）
    │
    └── 返回 order_id 给客户端
```

## 补偿操作（Rollback）

| 步骤 | 补偿操作 |
|------|---------|
| 库存已锁定，订单创建失败 | 调用 `inventory-service /release` 释放库存 |
| 优惠券已使用，后续失败 | 调用 `promotion-service /coupon/release` 恢复优惠券 |

## 幂等性保证

编排器通过 `request_id` 保证幂等性，相同 `request_id` 的重复请求直接返回首次结果：

```python
# order-orchestration 伪代码
async def checkout(request: CheckoutRequest):
    if await cache.get(f"checkout:{request.request_id}"):
        return await cache.get(f"checkout_result:{request.request_id}")
    # 执行 Saga ...
```

## 订单取消事件流

```
order.cancelled 事件
    ├── inventory-service：释放锁定库存
    └── notification-service：发送取消通知
```

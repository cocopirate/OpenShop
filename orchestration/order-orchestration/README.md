# Order Orchestration Service（订单编排服务）

订单流程编排服务，使用 Saga 模式协调跨服务的订单创建、支付、库存扣减等分布式事务。

## 职责

- 编排订单创建流程（校验 → 扣库存 → 创建订单 → 发起支付）
- 实现 Saga 补偿机制，保障分布式事务一致性
- 订单状态机管理
- 超时重试与幂等控制

## 流程示意

```
下单请求
  -> 校验促销 (promotion-service)
  -> 锁定库存 (inventory-service)
  -> 创建订单 (order-service)
  -> 发起支付通知 (notification-service)

补偿链（任意步骤失败时回滚）:
  <- 释放库存
  <- 取消订单
```

## 端口

- 服务端口: **8100**

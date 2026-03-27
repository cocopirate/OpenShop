# 业务流程

## 客户购物流程

```
客户注册/登录
    │
    ▼
浏览商品 → 搜索商品 → 查看 SKU
    │
    ▼
加入购物车 → 选择规格/数量
    │
    ▼
提交订单
    ├── 选择收货地址
    ├── 选择优惠券（可选）
    └── 确认支付金额
    │
    ▼
支付
    │
    ▼
等待商家发货
    │
    ▼
确认收货 → 评价
    │
    ▼
（如需）申请售后 → 退款/换货
```

## 商家运营流程

```
商家注册申请
    │
    ▼
提交营业执照等资质
    │
    ▼
平台审核（pending → approved / rejected）
    │
    ▼（审核通过）
创建店铺 → 上架商品（draft → online）
    │
    ▼
接收订单 → 备货 → 发货
    │
    ▼
处理售后申请
    │
    ▼
查看营收报表
```

## 下单完整事件链路

```
客户端 POST /api/v1/orchestration/checkout
    │
    ▼
order-orchestration（Saga 编排器）
    ├── 1. 校验优惠券 → promotion-service
    ├── 2. 锁定库存  → inventory-service
    ├── 3. 创建订单  → order-service
    │       └── 发布 order.created 事件
    └── 返回 order_id 给客户端

异步消费（RabbitMQ）
    ├── inventory-service  ← order.paid   → 扣减库存
    ├── notification-service ← order.created → 发送下单成功通知
    └── promotion-service  ← order.completed → 更新优惠券使用量
```

## 通知发送流程

详见 [通知系统](../02-user-guide/notification.md) 和 [架构：短信通知链路](../04-architecture/gateway.md)。

## 售后流程

```
客户申请售后（退款 / 退货 / 换货）
    │
    ▼
aftersale-service 创建售后单（pending_review）
    │
    ▼
商家/平台审核
    ├── 通过（approved） → 通知客户 → 处理退款/换货
    └── 拒绝（rejected） → 通知客户
    │
    ▼（审核通过后）
发布 aftersale.approved 事件
    ├── notification-service → 通知客户
    └── order-service → 更新订单状态
```

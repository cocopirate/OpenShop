# 下单流程

## 完整下单流程

```
浏览商品 → 加入购物车 → 填写订单信息 → 提交结账 → 支付 → 等待发货 → 确认收货
```

## 提交结账（Saga 编排）

结账通过 `order-orchestration` 服务使用 Saga 模式编排：

```http
POST /api/v1/orchestration/checkout
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "items": [
    {"sku_id": "sku_001", "quantity": 2},
    {"sku_id": "sku_002", "quantity": 1}
  ],
  "address_id": "addr_001",
  "coupon_code": "SAVE20",
  "request_id": "req-client-uuid-001"
}
```

**Saga 步骤：**

1. 校验优惠券（promotion-service）
2. 锁定库存（inventory-service）
3. 创建订单（order-service）
4. 返回 `order_id` 给客户端

任何步骤失败，前序步骤会自动补偿（如释放已锁定库存）。

## 订单状态流转

```
pending_payment → paid → shipped → completed
                      ↘           ↗
                       cancelled
```

| 状态 | 说明 |
|------|------|
| pending_payment | 待支付，库存已锁定 |
| paid | 已支付，等待商家发货 |
| shipped | 已发货 |
| completed | 订单完成，已确认收货 |
| cancelled | 已取消，库存已释放 |

## 取消订单

```http
POST /api/v1/orders/{order_id}/cancel
Authorization: Bearer <access_token>
```

取消后自动触发以下事件（异步）：
- `inventory-service`：释放锁定库存
- `notification-service`：发送取消通知

## 售后申请

订单完成后，客户可在一定时间内申请售后：

```http
POST /api/v1/aftersale
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "order_id": "order_001",
  "type": "refund",
  "reason": "商品与描述不符",
  "images": ["https://cdn.example.com/proof.jpg"]
}
```

售后类型：`refund`（退款）、`return`（退货）、`exchange`（换货）

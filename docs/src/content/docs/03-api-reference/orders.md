---
title: 订单管理 API
---

> 订单相关接口涉及 order-service（:8005）和 order-orchestration（:8100）。

## 提交结账（Saga）

通过编排服务创建订单，保证跨服务数据一致性：

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

**响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "order_id": "order_uuid",
    "total_amount": "168.00",
    "status": "pending_payment"
  }
}
```

## 获取订单详情

```http
GET /api/v1/orders/{order_id}
Authorization: Bearer <access_token>
```

## 获取订单列表

```http
GET /api/v1/orders?page=1&size=20&status=paid
Authorization: Bearer <access_token>
```

## 取消订单

```http
POST /api/v1/orders/{order_id}/cancel
Authorization: Bearer <access_token>
```

## 订单状态

| 状态 | 说明 |
|------|------|
| pending_payment | 待支付 |
| paid | 已支付 |
| shipped | 已发货 |
| completed | 已完成 |
| cancelled | 已取消 |

## 申请售后

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

## 发货（商家操作）

```http
POST /api/v1/orders/{order_id}/ship
Authorization: Bearer <merchant_token>
Content-Type: application/json

{
  "tracking_number": "SF1234567890",
  "carrier": "顺丰速运"
}
```

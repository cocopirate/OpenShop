# promotion-service（促销服务）

负责优惠券、满减、秒杀等促销活动的创建、管理与核销。

## 职责

- 优惠券发放与核销
- 满减活动配置
- 秒杀活动管理

## 主要接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `GET /api/v1/promotions/coupons/{code}/validate` | GET | 校验优惠券 |
| `POST /api/v1/promotions/coupons/{code}/redeem` | POST | 核销优惠券 |
| `GET /api/v1/promotions/flash-sales` | GET | 获取秒杀活动列表 |

## 数据模型

- Coupon
- CouponUsage
- DiscountRule
- FlashSale

## 依赖服务

- user-service（用户资格校验）
- order-service（通过 Kafka 监听订单完成事件）

## 端口

- 服务端口: **8007**

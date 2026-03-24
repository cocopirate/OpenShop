# aftersale-service（售后服务）

负责退款、退货、换货等售后流程管理。

## 职责

- 售后申请受理与审核
- 退款流程编排
- 退货/换货物流跟踪

## 主要接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `POST /api/v1/aftersale` | POST | 发起售后申请 |
| `GET /api/v1/aftersale/{request_id}` | GET | 查询售后详情 |
| `PUT /api/v1/aftersale/{request_id}/approve` | PUT | 审核通过售后 |

## 数据模型

- AftersaleRequest
- Refund
- ReturnShipment

## 依赖服务

- order-service（验证订单）
- notification-service（售后状态通知）

## 端口

- 服务端口: **8006**

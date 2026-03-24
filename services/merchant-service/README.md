# merchant-service（商家服务）

负责商家入驻、店铺信息管理及资质审核流程。

## 职责

- 商家入驻申请与审核
- 店铺信息维护
- 商家资质管理

## 主要接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `POST /api/v1/merchants` | POST | 商家入驻申请 |
| `GET /api/v1/merchants/{merchant_id}` | GET | 获取商家信息 |
| `GET /api/v1/merchants/{merchant_id}/shops` | GET | 获取商家店铺列表 |

## 数据模型

- Merchant
- Shop
- MerchantQualification

## 依赖服务

- user-service（验证用户身份）
- notification-service（审核结果通知）

## 端口

- 服务端口: **8002**

# 商家管理 API

> 以下接口由 merchant-service（:8002）提供，前缀 `/api/v1/merchants`。

## 提交入驻申请

```http
POST /api/v1/merchants/apply
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "business_name": "张记小店",
  "license_number": "91110000XXXXXXXXXX",
  "contact_name": "张三",
  "contact_phone": "13800138000"
}
```

**响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "merchant_id": "uuid",
    "status": "pending"
  }
}
```

## 获取商家详情

```http
GET /api/v1/merchants/{merchant_id}
Authorization: Bearer <access_token>
```

## 审核商家（管理员）

```http
POST /api/v1/admin/merchants/{merchant_id}/review
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "action": "approve",
  "remark": ""
}
```

`action` 可选值：`approve`（通过）、`reject`（拒绝）

## 商家状态

| 状态 | 说明 |
|------|------|
| pending | 待审核 |
| approved | 已通过 |
| rejected | 已拒绝 |
| suspended | 已暂停 |

## 获取商家列表（管理员）

```http
GET /api/v1/admin/merchants?page=1&size=20&status=pending
Authorization: Bearer <admin_token>
```

## 创建店铺

```http
POST /api/v1/merchants/shops
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "shop_name": "张记精品店",
  "description": "专营优质生活用品",
  "logo_url": "https://cdn.example.com/logo.jpg"
}
```

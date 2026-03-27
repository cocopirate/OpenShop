# 商家入驻

## 入驻流程

商家入驻分为以下几个阶段：

```
注册客户账号 → 提交入驻申请 → 平台审核 → 审核通过 → 创建店铺 → 上架商品
```

## 1. 注册客户账号

商家需先在平台注册普通客户账号（手机号 + 验证码）。

```http
POST /api/v1/users/register
Content-Type: application/json

{
  "phone": "13800138000",
  "sms_code": "123456",
  "nickname": "张老板"
}
```

## 2. 提交商家入驻申请

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

申请提交后，商家状态为 `pending`，等待平台审核。

## 3. 平台审核

平台运营人员通过管理后台（Admin BFF）审核入驻申请：

- **通过**：商家状态变更为 `approved`，发送短信通知
- **拒绝**：商家状态变更为 `rejected`，附带拒绝原因

## 4. 创建店铺

审核通过后，商家可以创建店铺：

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

## 5. 上架商品

```http
POST /api/v1/products
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "高品质棉质T恤",
  "description": "100%纯棉，多色可选",
  "category_id": "cat_clothing",
  "skus": [
    {
      "attributes": {"color": "白色", "size": "M"},
      "price": 89.00,
      "stock": 100
    },
    {
      "attributes": {"color": "黑色", "size": "L"},
      "price": 89.00,
      "stock": 80
    }
  ]
}
```

商品状态流转：`draft → online → offline`

## 商家状态说明

| 状态 | 说明 |
|------|------|
| pending | 待审核 |
| approved | 已通过，可正常运营 |
| rejected | 已拒绝，可重新申请 |
| suspended | 已暂停，违规处理中 |

# 领域模型文档

## 核心聚合根

### User（用户）
```
User
├── user_id: UUID (PK)
├── phone: str (unique)
├── email: Optional[str]
├── nickname: str
├── avatar_url: Optional[str]
├── status: Enum(active, disabled)
└── created_at: datetime
```

### Merchant（商家）
```
Merchant
├── merchant_id: UUID (PK)
├── user_id: UUID (FK -> User)
├── business_name: str
├── license_number: str
├── status: Enum(pending, approved, rejected, suspended)
└── shops: List[Shop]
```

### Product SPU（商品）
```
Product
├── product_id: UUID (PK)
├── merchant_id: UUID (FK -> Merchant)
├── name: str
├── description: str
├── category_id: UUID
├── skus: List[SKU]
└── status: Enum(draft, online, offline)

SKU
├── sku_id: UUID (PK)
├── product_id: UUID (FK -> Product)
├── attributes: JSON  # {color: "red", size: "XL"}
├── price: Decimal
└── stock: int
```

### Order（订单）
```
Order
├── order_id: UUID (PK)
├── user_id: UUID (FK -> User)
├── status: Enum(pending_payment, paid, shipped, completed, cancelled)
├── total_amount: Decimal
├── items: List[OrderItem]
└── created_at: datetime

OrderItem
├── item_id: UUID (PK)
├── order_id: UUID (FK -> Order)
├── sku_id: UUID (FK -> SKU)
├── quantity: int
└── unit_price: Decimal
```

### AftersaleRequest（售后申请）
```
AftersaleRequest
├── request_id: UUID (PK)
├── order_id: UUID (FK -> Order)
├── type: Enum(refund, return, exchange)
├── reason: str
├── status: Enum(pending_review, approved, rejected, completed)
└── created_at: datetime
```

### Coupon（优惠券）
```
Coupon
├── coupon_id: UUID (PK)
├── code: str (unique)
├── type: Enum(fixed, percentage)
├── value: Decimal
├── min_order_amount: Decimal
├── valid_from: datetime
├── valid_until: datetime
└── usage_limit: int
```

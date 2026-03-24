# dto（数据传输对象库）

使用 Pydantic v2 定义服务间 HTTP 调用共用的请求/响应 DTO。

## 内容

- **user_dto.py**：用户相关 DTO（UserDTO, CreateUserRequest）
- **order_dto.py**：订单相关 DTO（OrderDTO, OrderItemDTO）
- **product_dto.py**：商品相关 DTO（ProductDTO, SKUDTO）
- **inventory_dto.py**：库存相关 DTO（LockInventoryRequest）
- **notification_dto.py**：通知相关 DTO（SendNotificationRequest）

## 使用方式

```python
from libs.dto.order_dto import OrderDTO, CreateOrderRequest
from libs.dto.user_dto import UserDTO
```

## 技术依赖

- Python 3.11+
- Pydantic v2

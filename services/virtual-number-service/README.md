# virtual-number-service（隐私号能力服务）

提供号码隐私保护能力，为买卖双方通话绑定虚拟中间号，保护真实手机号。

## 职责

- 虚拟号码绑定与分配
- 绑定关系生命周期管理
- 通话记录查询

## 主要接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `POST /api/v1/virtual-numbers/bind` | POST | 创建号码绑定 |
| `DELETE /api/v1/virtual-numbers/{binding_id}` | DELETE | 释放号码绑定 |
| `GET /api/v1/virtual-numbers/{binding_id}/calls` | GET | 查询通话记录 |

## 数据模型

- VirtualNumberBinding
- CallRecord

## 依赖服务

- order-service（通过 RabbitMQ 监听订单事件触发绑定）

## 端口

- 服务端口: **8011**

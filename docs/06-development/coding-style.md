# 编码规范

## Python 版本

使用 Python 3.11+，利用新的类型注解语法（`list[str]` 而非 `List[str]`）。

## 代码风格

项目使用 **Ruff** 进行代码格式化和检查，配置与 PEP 8 兼容。

```bash
# 格式化
ruff format .

# 检查（含 lint）
ruff check .

# 自动修复
ruff check --fix .
```

## 命名约定

| 类型 | 规范 | 示例 |
|------|------|------|
| 变量/函数 | snake_case | `user_id`, `get_user` |
| 类 | PascalCase | `UserService`, `OrderRepository` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| 模块/包 | snake_case | `user_service`, `order_router` |
| Pydantic 模型字段 | snake_case | `created_at`, `phone_masked` |

## 类型注解

所有函数签名必须有完整类型注解：

```python
async def get_user(user_id: int, db: AsyncSession) -> UserSchema:
    ...
```

## 异步编程

所有 I/O 操作（数据库、Redis、HTTP）必须使用 `async/await`：

```python
# 正确
async def get_user(user_id: int) -> User:
    return await db.get(User, user_id)

# 错误（会阻塞事件循环）
def get_user(user_id: int) -> User:
    return db.get(User, user_id)
```

## 目录分层

遵循 **Repository Pattern**：

- `routers/`：仅负责 HTTP 路由，调用 services 层
- `services/`：业务逻辑，调用 repositories 层
- `repositories/`：数据访问，不包含业务逻辑

禁止在 routers 中直接操作数据库，禁止在 repositories 中写业务逻辑。

## 注释规范

- 复杂逻辑需加注释说明设计意图，而非解释代码本身
- 公共函数和类使用 docstring（Google 风格）：

```python
async def send_sms(phone: str, template_id: str, params: dict) -> SmsResult:
    """发送短信。

    Args:
        phone: 手机号，格式 13800138000
        template_id: 模板 ID，如 SMS_ORDER_SHIPPED
        params: 模板变量，如 {"orderId": "ORD-001"}

    Returns:
        SmsResult 包含 message_id 和发送状态

    Raises:
        SmsRateLimitError: 超出限流阈值
        SmsProviderError: 供应商调用失败
    """
```

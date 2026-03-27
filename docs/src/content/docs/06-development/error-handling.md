---
title: 错误处理
---

## 异常层次

```
BaseAppException
├── NotFoundError        # 404，资源不存在
├── ValidationError      # 422，参数校验失败
├── AuthenticationError  # 401，未认证
├── AuthorizationError   # 403，无权限
├── RateLimitError       # 429，超出限流
└── InternalError        # 500，服务内部错误
```

## 全局异常处理器

每个服务在 `main.py` 中注册全局异常处理器，将内部异常转换为统一响应格式：

```python
@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(
        status_code=404,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None,
            "request_id": request.state.request_id,
        },
    )
```

## 业务错误码

在 `libs/common/errors.py` 中统一定义：

```python
class ErrorCode:
    USER_NOT_FOUND = 40001
    USER_DISABLED = 40002
    ORDER_NOT_FOUND = 40201
    INVENTORY_INSUFFICIENT = 40301
    SMS_RATE_LIMIT = 40501
```

## 数据库错误处理

数据库层捕获 `asyncpg` 异常并转换为业务异常：

```python
try:
    await db.commit()
except UniqueViolationError:
    await db.rollback()
    raise DuplicateError("用户名已存在")
```

## 外部服务错误处理

调用外部服务时设置超时并处理异常：

```python
try:
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
except httpx.TimeoutException:
    raise InternalError("上游服务超时")
except httpx.HTTPStatusError as e:
    raise InternalError(f"上游服务异常: {e.response.status_code}")
```

## 不要吞掉异常

❌ 错误做法：
```python
try:
    result = await risky_operation()
except Exception:
    pass  # 静默忽略
```

✅ 正确做法：
```python
try:
    result = await risky_operation()
except Exception as e:
    logger.error("operation failed", error=str(e))
    raise InternalError("操作失败") from e
```

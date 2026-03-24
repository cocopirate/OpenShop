# common（公共工具库）

提供所有微服务共用的工具函数、中间件及基础类。

## 内容

- **response.py**：统一响应格式封装 `{code, message, data, request_id}`
- **exceptions.py**：业务异常基类与常见异常定义
- **middleware/logging.py**：结构化日志中间件（JSON 格式）
- **middleware/request_id.py**：请求链路 ID 注入中间件
- **pagination.py**：分页参数与分页响应模型

## 使用方式

```python
from libs.common.response import success_response, error_response
from libs.common.exceptions import BusinessException
from libs.common.pagination import PaginationParams, PaginatedResponse
```

## 技术依赖

- Python 3.11+
- FastAPI
- Pydantic v2

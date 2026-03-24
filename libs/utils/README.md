# utils（通用工具函数库）

提供无业务依赖的通用工具函数。

## 内容

- **datetime_utils.py**：时间格式化、时区转换
- **str_utils.py**：字符串处理、脱敏（手机号、身份证）
- **hash_utils.py**：哈希、加密工具
- **retry.py**：异步重试装饰器
- **circuit_breaker.py**：简单熔断器实现

## 使用方式

```python
from libs.utils.str_utils import mask_phone
from libs.utils.retry import async_retry
from libs.utils.datetime_utils import now_utc
```

## 技术依赖

- Python 3.11+
- tenacity（重试）

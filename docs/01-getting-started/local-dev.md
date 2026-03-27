# 本地开发

## 开发环境搭建

### 1. 安装 uv

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. 创建虚拟环境

```bash
cd OpenShop
uv venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
```

### 3. 安装依赖

每个服务有独立的 `requirements.txt`，以 consumer-service 为例：

```bash
cd services/consumer-service
uv pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
```

`.env` 文件说明：

```bash
DATABASE_URL=postgresql+asyncpg://openshop:openshop123@localhost:5432/openshop
REDIS_URL=redis://:redis123@localhost:6379/0
RABBITMQ_URL=amqp://openshop:openshop123@localhost:5672/
SECRET_KEY=your-secret-key-here
DEBUG=true
```

### 5. 单独启动某个服务

```bash
cd services/consumer-service
uvicorn app.main:app --reload --port 8001
```

## 数据库迁移

项目使用 Alembic 管理数据库迁移：

```bash
cd services/consumer-service

# 生成迁移文件
alembic revision --autogenerate -m "add user table"

# 执行迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

## 运行测试

```bash
cd services/consumer-service

# 运行所有测试
pytest

# 带覆盖率
pytest --cov=app --cov-report=term-missing

# 只运行单元测试
pytest tests/unit/
```

## IDE 配置

项目包含 `.vscode/settings.json`，建议使用 VSCode 并安装以下插件：
- Python
- Pylance
- Ruff（代码格式化）

## 常用命令

```bash
# 格式化代码
ruff format .

# 代码检查
ruff check .

# 类型检查
mypy app/
```

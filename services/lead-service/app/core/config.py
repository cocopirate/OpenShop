from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "lead-service"
    SERVICE_PORT: int = 8012
    DEBUG: bool = False
    ENV: str = "development"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://openshop:openshop123@localhost:5432/openshop"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # Redis
    REDIS_URL: str = "redis://:redis123@localhost:6379/0"
    REDIS_POOL_MAX_SIZE: int = 10

    # RabbitMQ
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"

    # Downstream services
    PRODUCT_SERVICE_URL: str = "http://product-service:8003"
    ORDER_SERVICE_URL: str = "http://order-service:8005"

    model_config = {
        "env_file": [".env", ".env.local"],
        "env_file_encoding": "utf-8",
    }


settings = Settings()

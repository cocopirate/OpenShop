from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Priority (high → low): system env vars > .env > .env.local
    # pydantic-settings resolves env_file list left-to-right, earlier files win.
    model_config = {
        "env_file": [".env", ".env.local"],
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    SERVICE_NAME: str = "sms-service"
    SERVICE_PORT: int = 8010
    DEBUG: bool = False
    ENV: str = "development"

    # Database – defaults are local docker-compose values; override in production
    DATABASE_URL: str = "postgresql+asyncpg://openshop:openshop123@localhost:5432/openshop"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # Redis – defaults are local docker-compose values; override in production
    REDIS_URL: str = "redis://:redis123@localhost:6379/0"
    REDIS_POOL_MIN_SIZE: int = 2
    REDIS_POOL_MAX_SIZE: int = 10

    # RabbitMQ (optional consumer)
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"

    # OpenTelemetry / ARMS
    OTEL_ENDPOINT: str = ""
    OTEL_TOKEN: str = ""


settings = Settings()

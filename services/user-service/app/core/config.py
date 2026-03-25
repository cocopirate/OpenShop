from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "user-service"
    SERVICE_PORT: int = 8001
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

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    # Security
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = {
        # Priority (high → low): system env vars > .env > .env.local
        # pydantic-settings resolves env_file list left-to-right, earlier files win.
        "env_file": [".env", ".env.local"],
        "env_file_encoding": "utf-8",
    }


settings = Settings()

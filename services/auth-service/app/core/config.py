from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "auth-service"
    SERVICE_PORT: int = 8000
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

    # Security
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Upstream services
    MERCHANT_SERVICE_URL: str = "http://merchant-service:8002"
    ADMIN_SERVICE_URL: str = "http://admin-service:8012"
    SMS_SERVICE_URL: str = "http://sms-service:8010"
    CONSUMER_SERVICE_URL: str = "http://consumer-service:8001"

    model_config = {
        "env_file": [".env", ".env.local"],
        "env_file_encoding": "utf-8",
    }


settings = Settings()

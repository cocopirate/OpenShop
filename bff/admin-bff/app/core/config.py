from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "admin-bff"
    SERVICE_PORT: int = 8091
    DEBUG: bool = False
    ENV: str = "development"

    # Upstream service URLs
    PRODUCT_SERVICE_URL: str = "http://product-service:8003"
    AUTH_SERVICE_URL: str = "http://auth-service:8000"
    ADMIN_SERVICE_URL: str = "http://admin-service:8012"
    MERCHANT_SERVICE_URL: str = "http://merchant-service:8002"
    ORDER_SERVICE_URL: str = "http://order-service:8005"

    # Redis
    REDIS_URL: str = "redis://:redis123@localhost:6379/0"
    REDIS_POOL_MAX_SIZE: int = 10

    model_config = {
        "env_file": [".env", ".env.local"],
        "env_file_encoding": "utf-8",
    }


settings = Settings()

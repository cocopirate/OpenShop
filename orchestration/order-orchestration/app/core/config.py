from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "order-orchestration"
    SERVICE_PORT: int = 8100
    DEBUG: bool = False

    # Required: set via environment variables or .env file (see .env.example)
    DATABASE_URL: str
    REDIS_URL: str
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    USER_SERVICE_URL: str = "http://user-service:8001"
    INVENTORY_SERVICE_URL: str = "http://inventory-service:8004"
    ORDER_SERVICE_URL: str = "http://order-service:8005"
    PROMOTION_SERVICE_URL: str = "http://promotion-service:8007"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8009"

    class Config:
        env_file = ".env"


settings = Settings()

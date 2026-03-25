from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "notification-service"
    SERVICE_PORT: int = 8009
    DEBUG: bool = False

    # Required: set via environment variables or .env file (see .env.example)
    DATABASE_URL: str
    REDIS_URL: str
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    # Downstream capability services
    SMS_SERVICE_URL: str = "http://sms-service:8010"

    class Config:
        env_file = ".env"


settings = Settings()

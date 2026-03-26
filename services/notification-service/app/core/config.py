from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "notification-service"
    SERVICE_PORT: int = 8009
    DEBUG: bool = False

    # Required: set via environment variables or .env file (see .env.example)
    DATABASE_URL: str
    REDIS_URL: str
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"

    # Downstream capability services
    SMS_SERVICE_URL: str = "http://sms-service:8010"

    class Config:
        env_file = ".env"


settings = Settings()

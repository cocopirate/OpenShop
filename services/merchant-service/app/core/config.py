from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "merchant-service"
    SERVICE_PORT: int = 8002
    DEBUG: bool = False

    # Required: set via environment variables or .env file (see .env.example)
    DATABASE_URL: str
    REDIS_URL: str
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"

    class Config:
        env_file = ".env"


settings = Settings()

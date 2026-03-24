from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "promotion-service"
    SERVICE_PORT: int = 8007
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://openshop:openshop123@localhost:5432/openshop"
    REDIS_URL: str = "redis://:redis123@localhost:6379/0"
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    class Config:
        env_file = ".env"


settings = Settings()

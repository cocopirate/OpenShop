from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "seo-service"
    SERVICE_PORT: int = 8020
    DEBUG: bool = False
    APP_ENV: str = "development"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://openshop:openshop123@localhost:5432/seo_db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # Redis (ARQ broker)
    REDIS_URL: str = "redis://localhost:6379/0"

    # OpenAI
    OPENAI_API_KEY: str = "sk-placeholder"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Duplicate detection
    DUPLICATE_THRESHOLD: float = 0.75
    MAX_RETRIES: int = 3

    model_config = {
        "env_file": [".env", ".env.local"],
        "env_file_encoding": "utf-8",
    }


settings = Settings()

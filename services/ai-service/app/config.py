from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "ai-service"
    SERVICE_PORT: int = 8021
    DEBUG: bool = False
    APP_ENV: str = "development"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://openshop:openshop123@localhost:5432/ai_service_db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI providers
    OPENAI_API_KEY: str = "sk-placeholder"
    OPENAI_DEFAULT_MODEL: str = "gpt-4o-mini"

    # Aliyun Dashscope (Qwen / 百炼平台)
    DASHSCOPE_API_KEY: str = "sk-placeholder"
    QWEN_DEFAULT_MODEL: str = "qwen-plus"

    # Service-to-service auth keys
    SERVICE_KEY_SEO: str = ""
    SERVICE_KEY_CS: str = ""

    # Rate limiting defaults
    RATE_LIMIT_RPM: int = 60
    RATE_LIMIT_TPM: int = 100000

    # Cache
    CACHE_DEFAULT_TTL: int = 3600

    model_config = {
        "env_file": [".env", ".env.local"],
        "env_file_encoding": "utf-8",
    }

    def get_service_keys(self) -> dict[str, str]:
        """Return mapping of service key value -> service name."""
        keys: dict[str, str] = {}
        if self.SERVICE_KEY_SEO:
            keys[self.SERVICE_KEY_SEO] = "seo-service"
        if self.SERVICE_KEY_CS:
            keys[self.SERVICE_KEY_CS] = "cs-service"
        return keys


settings = Settings()

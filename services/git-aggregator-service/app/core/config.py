from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "git-aggregator-service"
    SERVICE_PORT: int = 8000
    DEBUG: bool = False
    ENV: str = "development"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://openshop:openshop123@localhost:5432/openshop"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # Webhook secrets
    CODEUP_TOKEN: str = "change-this-codeup-token"
    GITHUB_WEBHOOK_SECRET: str = "change-this-github-secret"
    GITLAB_TOKEN: str = "change-this-gitlab-token"

    # Optional comma-separated IP whitelist (empty string = disabled)
    IP_WHITELIST: str = ""

    # Anti-replay window in seconds
    MAX_TIMESTAMP_DELAY: int = 300

    model_config = {
        "env_file": [".env", ".env.local"],
        "env_file_encoding": "utf-8",
    }


settings = Settings()

"""Captcha-service application settings."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {
        "env_file": [".env", ".env.local"],
        "env_file_encoding": "utf-8",
    }

    SERVICE_NAME: str = "captcha-service"
    SERVICE_PORT: int = 8020
    DEBUG: bool = False
    ENV: str = "development"

    # Redis
    REDIS_URL: str = "redis://:redis123@localhost:6379/0"
    REDIS_POOL_MAX_SIZE: int = 10

    # Security
    CAPTCHA_SECRET_KEY: str = "change-this-secret-key-in-production"
    CAPTCHA_AES_KEY: str = "0" * 64  # 32-byte hex string

    # Challenge TTL (seconds)
    CHALLENGE_TTL: int = 120

    # Verification token TTL (seconds)
    TOKEN_TTL: int = 300

    # Accepted gesture duration range (ms)
    MIN_GESTURE_DURATION_MS: int = 200
    MAX_GESTURE_DURATION_MS: int = 15000

    # Score thresholds
    SCORE_PASS_THRESHOLD: float = 0.7
    SCORE_REJECT_THRESHOLD: float = 0.4


settings = Settings()

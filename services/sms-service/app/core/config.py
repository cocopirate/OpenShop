from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Priority (high → low): system env vars > .env > .env.local
    # pydantic-settings resolves env_file list left-to-right, earlier files win.
    model_config = {
        "env_file": [".env", ".env.local"],
        "env_file_encoding": "utf-8",
    }

    SERVICE_NAME: str = "sms-service"
    SERVICE_PORT: int = 8010
    DEBUG: bool = False
    ENV: str = "development"

    # Database – defaults are local docker-compose values; override in production
    DATABASE_URL: str = "postgresql+asyncpg://openshop:openshop123@localhost:5432/openshop"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # Redis – defaults are local docker-compose values; override in production
    REDIS_URL: str = "redis://:redis123@localhost:6379/0"
    REDIS_POOL_MIN_SIZE: int = 2
    REDIS_POOL_MAX_SIZE: int = 10

    # RabbitMQ (optional consumer)
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"

    # SMS providers – Aliyun
    ALIYUN_ACCESS_KEY_ID: str = ""
    ALIYUN_ACCESS_KEY_SECRET: str = ""
    ALIYUN_SMS_SIGN_NAME: str = ""
    ALIYUN_SMS_ENDPOINT: str = "dysmsapi.aliyuncs.com"

    # SMS providers – Tencent Cloud
    TENCENT_SECRET_ID: str = ""
    TENCENT_SECRET_KEY: str = ""
    TENCENT_SMS_APP_ID: str = ""
    TENCENT_SMS_SIGN_NAME: str = ""

    # SMS providers – ChuangLan (创蓝云)
    CHUANGLAN_ACCOUNT: str = ""
    CHUANGLAN_PASSWORD: str = ""
    CHUANGLAN_API_URL: str = "https://smssh1.253.com/msg/v1/send/json"

    # Active provider: "aliyun" | "tencent" | "chuanglan"
    SMS_PROVIDER: str = "chuanglan"
    # Fallback provider (used when primary circuit is open)
    SMS_PROVIDER_FALLBACK: str = ""
    # Circuit breaker: consecutive failures before switching
    SMS_PROVIDER_FAILURE_THRESHOLD: int = 3
    # Circuit breaker: seconds before attempting recovery
    SMS_PROVIDER_RECOVERY_TIMEOUT: int = 60

    # Verification code TTL (seconds)
    SMS_CODE_TTL: int = 300

    # Rate limits
    SMS_RATE_LIMIT_PHONE_PER_MINUTE: int = 1
    SMS_RATE_LIMIT_PHONE_PER_DAY: int = 10
    SMS_RATE_LIMIT_IP_PER_MINUTE: int = 10
    SMS_RATE_LIMIT_IP_PER_DAY: int = 100

    # Records retention (days; 0 = no cleanup)
    SMS_RECORDS_RETENTION_DAYS: int = 90

    # OpenTelemetry / ARMS
    OTEL_ENDPOINT: str = ""
    OTEL_TOKEN: str = ""


settings = Settings()

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env"}

    SERVICE_NAME: str = "sms-service"
    SERVICE_PORT: int = 8010
    DEBUG: bool = False
    ENV: str = "development"

    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # Redis
    REDIS_URL: str
    REDIS_POOL_MIN_SIZE: int = 2
    REDIS_POOL_MAX_SIZE: int = 10

    # Kafka (optional consumer)
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

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

    # Active provider: "aliyun" | "tencent" | "chuanglan"
    SMS_PROVIDER: str = "aliyun"
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

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env"}

    SERVICE_NAME: str = "sms-service"
    SERVICE_PORT: int = 8010
    DEBUG: bool = False

    # Database – cloud PostgreSQL
    DATABASE_URL: str
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # Redis – cloud Redis
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

    # Active provider: "aliyun" | "tencent"
    SMS_PROVIDER: str = "aliyun"

    # Verification code TTL (seconds)
    SMS_CODE_TTL: int = 300


settings = Settings()

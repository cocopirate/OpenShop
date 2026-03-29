from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Priority (high → low): system env vars > .env > .env.local
    # pydantic-settings resolves env_file list left-to-right, earlier files win.
    # extra = "allow" lets load_persisted_config() set SMS provider attributes
    # at runtime without them being backed by environment variables.
    model_config = {
        "env_file": [".env", ".env.local"],
        "env_file_encoding": "utf-8",
        "extra": "allow",
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

    # OpenTelemetry / ARMS
    OTEL_ENDPOINT: str = ""
    OTEL_TOKEN: str = ""


settings = Settings()

# ---------------------------------------------------------------------------
# SMS provider config – NOT loaded from environment variables.
#
# These defaults are applied once at module import and are overridden at
# service startup by load_persisted_config(), which reads the
# sms_config_store table written via PUT /api/sms/config.
#
# To change any of these values use the runtime API, not env vars.
# ---------------------------------------------------------------------------

_SMS_DEFAULTS: dict = {
    # Active provider and circuit-breaker
    "SMS_PROVIDER": "chuanglan",
    "SMS_PROVIDER_FALLBACK": "",
    "SMS_PROVIDER_FAILURE_THRESHOLD": 3,
    "SMS_PROVIDER_RECOVERY_TIMEOUT": 60,
    # Verification code
    "SMS_CODE_TTL": 300,
    # Rate limits
    "SMS_RATE_LIMIT_PHONE_PER_MINUTE": 1,
    "SMS_RATE_LIMIT_PHONE_PER_DAY": 10,
    "SMS_RATE_LIMIT_IP_PER_MINUTE": 10,
    "SMS_RATE_LIMIT_IP_PER_DAY": 100,
    # Record retention
    "SMS_RECORDS_RETENTION_DAYS": 90,
    # Multi-tenant channel routing
    "SMS_CHANNELS": {},
    "SMS_CLIENT_KEYS": {},
    # ChuangLan (创蓝云) credentials
    "CHUANGLAN_ACCOUNT": "",
    "CHUANGLAN_PASSWORD": "",
    "CHUANGLAN_API_URL": "https://smssh1.253.com/msg/v1/send/json",
    # Aliyun SMS credentials
    "ALIYUN_ACCESS_KEY_ID": "",
    "ALIYUN_ACCESS_KEY_SECRET": "",
    "ALIYUN_SMS_SIGN_NAME": "",
    "ALIYUN_SMS_ENDPOINT": "dysmsapi.aliyuncs.com",
    # Aliyun Phone Number Service credentials
    "ALIYUN_PHONE_SVC_ACCESS_KEY_ID": "",
    "ALIYUN_PHONE_SVC_ACCESS_KEY_SECRET": "",
    "ALIYUN_PHONE_SVC_SIGN_NAME": "",
    "ALIYUN_PHONE_SVC_ENDPOINT": "dypnsapi.aliyuncs.com",
    # Tencent Cloud SMS credentials
    "TENCENT_SECRET_ID": "",
    "TENCENT_SECRET_KEY": "",
    "TENCENT_SMS_APP_ID": "",
    "TENCENT_SMS_SIGN_NAME": "",
}

for _k, _v in _SMS_DEFAULTS.items():
    setattr(settings, _k, _v)

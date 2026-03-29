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
# SMS runtime config – NOT loaded from environment variables.
#
# All provider credentials and routing strategy now live inside individual
# channel entries (SMS_CHANNELS). Configure them via:
#   PUT /api/sms/channels/{channel_name}
#
# The only global settings here are: default channel selection, code TTL,
# rate limits, retention policy, and the channel/client-key registries.
# ---------------------------------------------------------------------------

_SMS_DEFAULTS: dict = {
    # Default channel used when no X-API-Key / channel is specified.
    # Configure this channel (e.g. "_default") via PUT /api/sms/channels/_default.
    "SMS_DEFAULT_CHANNEL": "_default",
    # Verification code
    "SMS_CODE_TTL": 300,
    # Rate limits
    "SMS_RATE_LIMIT_PHONE_PER_MINUTE": 1,
    "SMS_RATE_LIMIT_PHONE_PER_DAY": 10,
    "SMS_RATE_LIMIT_IP_PER_MINUTE": 10,
    "SMS_RATE_LIMIT_IP_PER_DAY": 100,
    # Record retention
    "SMS_RECORDS_RETENTION_DAYS": 90,
    # Channel registry and client-key → channel mapping
    "SMS_CHANNELS": {},
    "SMS_CLIENT_KEYS": {},
}

for _k, _v in _SMS_DEFAULTS.items():
    setattr(settings, _k, _v)

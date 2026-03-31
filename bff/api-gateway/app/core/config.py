from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {
        "env_file": [".env", ".env.local"],
        "env_file_encoding": "utf-8",
    }

    SERVICE_NAME: str = "api-gateway"
    SERVICE_PORT: int = 8080
    DEBUG: bool = False
    ENV: str = "development"

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_MAX_SIZE: int = 10

    # JWT settings - must match auth-service
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"

    # Upstream services
    CONSUMER_SERVICE_URL: str = "http://consumer-service:8001"
    ADMIN_SERVICE_URL: str = "http://admin-service:8012"
    MERCHANT_SERVICE_URL: str = "http://merchant-service:8002"
    PRODUCT_SERVICE_URL: str = "http://product-service:8003"
    INVENTORY_SERVICE_URL: str = "http://inventory-service:8004"
    ORDER_SERVICE_URL: str = "http://order-service:8005"
    AFTERSALE_SERVICE_URL: str = "http://aftersale-service:8006"
    PROMOTION_SERVICE_URL: str = "http://promotion-service:8007"
    LOCATION_SERVICE_URL: str = "http://location-service:8008"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8009"
    SMS_SERVICE_URL: str = "http://sms-service:8010"
    AUTH_SERVICE_URL: str = "http://auth-service:8000"

    # BFF services
    APP_BFF_URL: str = "http://app-bff:8090"
    ADMIN_BFF_URL: str = "http://admin-bff:8091"

    # Rate limits
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # ---------------------------------------------------------------------------
    # Crypto / security settings
    # ---------------------------------------------------------------------------

    # RSA-2048/4096 private key in PEM format (used to decrypt AES session keys
    # that clients encrypt with the corresponding public key).
    # Leave empty to disable request-decryption entirely.
    CRYPTO_RSA_PRIVATE_KEY: str = ""

    # Shared HMAC-SHA256 secret used for request signature verification.
    # Leave empty to disable signature verification.
    CRYPTO_HMAC_SECRET: str = ""


settings = Settings()

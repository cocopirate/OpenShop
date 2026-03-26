import json

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env"}

    SERVICE_NAME: str = "api-gateway"
    SERVICE_PORT: int = 8080
    DEBUG: bool = False
    ENV: str = "development"

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_MAX_SIZE: int = 10

    # JWT settings - must match user-service
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"

    # Upstream services
    USER_SERVICE_URL: str = "http://user-service:8001"
    MERCHANT_SERVICE_URL: str = "http://merchant-service:8002"
    PRODUCT_SERVICE_URL: str = "http://product-service:8003"
    INVENTORY_SERVICE_URL: str = "http://inventory-service:8004"
    ORDER_SERVICE_URL: str = "http://order-service:8005"
    AFTERSALE_SERVICE_URL: str = "http://aftersale-service:8006"
    PROMOTION_SERVICE_URL: str = "http://promotion-service:8007"
    LOCATION_SERVICE_URL: str = "http://location-service:8008"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8009"
    SMS_SERVICE_URL: str = "http://sms-service:8010"

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
    # Leave empty to disable signature verification even if paths are listed.
    CRYPTO_HMAC_SECRET: str = ""

    # JSON list of path *prefixes* whose requests must carry a valid
    # X-Timestamp / X-Sign header pair.
    # Example: '["/api/v1/orders", "/api/v1/payments"]'
    CRYPTO_SIGN_PATHS_JSON: str = "[]"

    # JSON list of path *prefixes* whose request bodies are hybrid-encrypted
    # (AES-256-CBC body + RSA-OAEP encrypted AES key).
    # Example: '["/api/v1/orders"]'
    CRYPTO_ENCRYPT_REQUEST_PATHS_JSON: str = "[]"

    # JSON list of path *prefixes* whose responses should be AES-encrypted.
    # These paths must also be in CRYPTO_ENCRYPT_REQUEST_PATHS_JSON so that
    # the session AES key is available for response encryption.
    # Example: '["/api/v1/orders"]'
    CRYPTO_ENCRYPT_RESPONSE_PATHS_JSON: str = "[]"

    @property
    def CRYPTO_SIGN_PATHS(self) -> list[str]:
        return json.loads(self.CRYPTO_SIGN_PATHS_JSON)

    @property
    def CRYPTO_ENCRYPT_REQUEST_PATHS(self) -> list[str]:
        return json.loads(self.CRYPTO_ENCRYPT_REQUEST_PATHS_JSON)

    @property
    def CRYPTO_ENCRYPT_RESPONSE_PATHS(self) -> list[str]:
        return json.loads(self.CRYPTO_ENCRYPT_RESPONSE_PATHS_JSON)


settings = Settings()

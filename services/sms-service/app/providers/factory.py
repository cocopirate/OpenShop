"""SMS provider factory with per-channel circuit-breaker and fallback."""
import time
from typing import Optional

import structlog

from app.providers import BaseSmsProvider

log = structlog.get_logger(__name__)

# Per-channel in-memory circuit breaker state: {channel_name: {failure_count, last_failure_time, open}}
_circuits: dict = {}

_DEFAULT_FAILURE_THRESHOLD = 3
_DEFAULT_RECOVERY_TIMEOUT = 60


def _get_circuit(channel: str) -> dict:
    if channel not in _circuits:
        _circuits[channel] = {"failure_count": 0, "last_failure_time": 0.0, "open": False}
    return _circuits[channel]


def _make_provider(name: str, credentials: dict) -> BaseSmsProvider:
    if name == "tencent":
        from app.providers.tencent import TencentSmsProvider
        return TencentSmsProvider(
            secret_id=credentials.get("secret_id", ""),
            secret_key=credentials.get("secret_key", ""),
            app_id=credentials.get("app_id", ""),
            sign_name=credentials.get("sign_name", ""),
        )
    if name == "chuanglan":
        from app.providers.chuanglan import ChuangLanSmsProvider
        return ChuangLanSmsProvider(
            account=credentials.get("account", ""),
            password=credentials.get("password", ""),
            api_url=credentials.get("api_url", ""),
        )
    if name == "aliyun_phone_svc":
        from app.providers.aliyun_phone_svc import AliyunPhoneSvcProvider
        return AliyunPhoneSvcProvider(
            access_key_id=credentials.get("access_key_id", ""),
            access_key_secret=credentials.get("access_key_secret", ""),
            sign_name=credentials.get("sign_name", ""),
            endpoint=credentials.get("endpoint", ""),
        )
    from app.providers.aliyun import AliyunSmsProvider
    return AliyunSmsProvider(
        key_id=credentials.get("access_key_id", ""),
        key_secret=credentials.get("access_key_secret", ""),
        sign_name=credentials.get("sign_name", ""),
        endpoint=credentials.get("endpoint", ""),
    )


def get_provider(
    channel_name: str,
    channel_credentials: dict,
    failure_threshold: int = _DEFAULT_FAILURE_THRESHOLD,
    recovery_timeout: int = _DEFAULT_RECOVERY_TIMEOUT,
    fallback_channel_name: Optional[str] = None,
    fallback_credentials: Optional[dict] = None,
) -> BaseSmsProvider:
    """Return the active provider for *channel_name*.

    Circuit breaker parameters and fallback routing now come from the
    associated SmsPolicy rather than from the channel config itself.

    Args:
        channel_name: The name of the primary channel.
        channel_credentials: Dict of provider credentials for the channel
            (provider, access_key_id, access_key_secret, …).
        failure_threshold: Number of consecutive failures to open the circuit.
        recovery_timeout: Seconds to wait before attempting recovery.
        fallback_channel_name: Name of the fallback channel (from policy).
        fallback_credentials: Credentials dict for the fallback channel.
    """
    now = time.monotonic()
    circuit = _get_circuit(channel_name)

    # Half-open: attempt recovery after timeout
    if circuit["open"] and (now - circuit["last_failure_time"]) >= recovery_timeout:
        circuit["open"] = False
        circuit["failure_count"] = 0
        log.warning("sms.circuit_breaker.half_open", channel=channel_name)

    if circuit["open"] and fallback_channel_name and fallback_channel_name != channel_name:
        if fallback_credentials:
            log.warning(
                "sms.circuit_breaker.using_fallback",
                channel=channel_name,
                fallback=fallback_channel_name,
            )
            provider_name = fallback_credentials.get("provider", "aliyun")
            return _make_provider(provider_name, fallback_credentials)

    provider_name = channel_credentials.get("provider", "aliyun")
    log.info("sms.channel.routing", channel=channel_name, provider=provider_name)
    return _make_provider(provider_name, channel_credentials)


def record_provider_failure(channel: str, failure_threshold: int = _DEFAULT_FAILURE_THRESHOLD) -> None:
    """Record a provider failure for *channel*; open circuit if threshold exceeded."""
    circuit = _get_circuit(channel)
    circuit["failure_count"] += 1
    circuit["last_failure_time"] = time.monotonic()
    if circuit["failure_count"] >= failure_threshold:
        if not circuit["open"]:
            log.error(
                "sms.circuit_breaker.open",
                channel=channel,
                failure_count=circuit["failure_count"],
                threshold=failure_threshold,
            )
        circuit["open"] = True


def record_provider_success(channel: str) -> None:
    """Reset failure counter and close circuit for *channel* on success."""
    circuit = _get_circuit(channel)
    circuit["failure_count"] = 0
    circuit["open"] = False

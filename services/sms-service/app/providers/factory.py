"""SMS provider factory with per-channel circuit-breaker and fallback."""
import time

import structlog

from app.core.config import settings
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


def get_provider(channel: str) -> BaseSmsProvider:
    """Return the active provider for *channel*.

    Each channel carries its own provider credentials and optional strategy fields:
    - ``failure_threshold`` (int, default 3)
    - ``recovery_timeout``  (int seconds, default 60)
    - ``fallback_channel``  (str, optional – used when the circuit is open)

    If the channel's circuit breaker is open and a ``fallback_channel`` is
    configured, the fallback channel's provider is used instead.
    """
    channel_cfg = settings.SMS_CHANNELS.get(channel, {})
    threshold = int(channel_cfg.get("failure_threshold", _DEFAULT_FAILURE_THRESHOLD))
    recovery = int(channel_cfg.get("recovery_timeout", _DEFAULT_RECOVERY_TIMEOUT))
    fallback = channel_cfg.get("fallback_channel", "")

    now = time.monotonic()
    circuit = _get_circuit(channel)

    # Half-open: attempt recovery after timeout
    if circuit["open"] and (now - circuit["last_failure_time"]) >= recovery:
        circuit["open"] = False
        circuit["failure_count"] = 0
        log.warning("sms.circuit_breaker.half_open", channel=channel)

    if circuit["open"] and fallback and fallback != channel:
        log.warning("sms.circuit_breaker.using_fallback", channel=channel, fallback=fallback)
        fallback_cfg = settings.SMS_CHANNELS.get(fallback, {})
        provider_name = fallback_cfg.get("provider", "aliyun")
        return _make_provider(provider_name, fallback_cfg)

    provider_name = channel_cfg.get("provider", "aliyun")
    log.info("sms.channel.routing", channel=channel, provider=provider_name)
    return _make_provider(provider_name, channel_cfg)


def record_provider_failure(channel: str) -> None:
    """Record a provider failure for *channel*; open circuit if threshold exceeded."""
    channel_cfg = settings.SMS_CHANNELS.get(channel, {})
    threshold = int(channel_cfg.get("failure_threshold", _DEFAULT_FAILURE_THRESHOLD))
    circuit = _get_circuit(channel)
    circuit["failure_count"] += 1
    circuit["last_failure_time"] = time.monotonic()
    if circuit["failure_count"] >= threshold:
        if not circuit["open"]:
            log.error(
                "sms.circuit_breaker.open",
                channel=channel,
                failure_count=circuit["failure_count"],
                threshold=threshold,
            )
        circuit["open"] = True


def record_provider_success(channel: str) -> None:
    """Reset failure counter and close circuit for *channel* on success."""
    circuit = _get_circuit(channel)
    circuit["failure_count"] = 0
    circuit["open"] = False

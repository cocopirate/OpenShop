"""SMS provider factory with circuit-breaker fallback."""
import time
from typing import Optional

import structlog

from app.core.config import settings
from app.providers import BaseSmsProvider

log = structlog.get_logger(__name__)

# In-memory circuit breaker state (per process)
_circuit: dict = {
    "failure_count": 0,
    "last_failure_time": 0.0,
    "open": False,
}


def _make_provider(name: str, credentials: Optional[dict] = None) -> BaseSmsProvider:
    creds = credentials or {}
    if name == "tencent":
        from app.providers.tencent import TencentSmsProvider
        return TencentSmsProvider()
    if name == "chuanglan":
        from app.providers.chuanglan import ChuangLanSmsProvider
        return ChuangLanSmsProvider()
    if name == "aliyun_phone_svc":
        from app.providers.aliyun_phone_svc import AliyunPhoneSvcProvider
        return AliyunPhoneSvcProvider(
            access_key_id=creds.get("access_key_id") or settings.ALIYUN_PHONE_SVC_ACCESS_KEY_ID,
            access_key_secret=creds.get("access_key_secret") or settings.ALIYUN_PHONE_SVC_ACCESS_KEY_SECRET,
            sign_name=creds.get("sign_name") or settings.ALIYUN_PHONE_SVC_SIGN_NAME,
            endpoint=creds.get("endpoint") or settings.ALIYUN_PHONE_SVC_ENDPOINT,
        )
    from app.providers.aliyun import AliyunSmsProvider
    return AliyunSmsProvider(
        key_id=creds.get("access_key_id") or settings.ALIYUN_ACCESS_KEY_ID,
        key_secret=creds.get("access_key_secret") or settings.ALIYUN_ACCESS_KEY_SECRET,
        sign_name=creds.get("sign_name") or settings.ALIYUN_SMS_SIGN_NAME,
        endpoint=creds.get("endpoint") or settings.ALIYUN_SMS_ENDPOINT,
    )


def get_provider(channel: Optional[str] = None) -> BaseSmsProvider:
    """Return the active provider, optionally routed by named channel.

    If *channel* is given and found in ``settings.SMS_CHANNELS``, the
    channel's own provider type and credentials are used (bypassing the
    circuit-breaker fallback logic – channels are dedicated routes).
    Otherwise the default primary/fallback provider selection applies.
    """
    if channel:
        channel_cfg = settings.SMS_CHANNELS.get(channel)
        if channel_cfg:
            provider_name = channel_cfg.get("provider", settings.SMS_PROVIDER)
            log.info("sms.channel.routing", channel=channel, provider=provider_name)
            return _make_provider(provider_name, credentials=channel_cfg)
        log.warning("sms.channel.not_found", channel=channel)

    primary = settings.SMS_PROVIDER
    fallback = settings.SMS_PROVIDER_FALLBACK

    now = time.monotonic()
    # Half-open: attempt recovery after timeout
    if _circuit["open"] and (now - _circuit["last_failure_time"]) >= settings.SMS_PROVIDER_RECOVERY_TIMEOUT:
        _circuit["open"] = False
        _circuit["failure_count"] = 0
        log.warning("sms.circuit_breaker.half_open", provider=primary)

    if _circuit["open"] and fallback and fallback != primary:
        log.warning("sms.circuit_breaker.using_fallback", primary=primary, fallback=fallback)
        return _make_provider(fallback)

    return _make_provider(primary)


def record_provider_failure() -> None:
    """Record a provider failure; open circuit if threshold exceeded."""
    _circuit["failure_count"] += 1
    _circuit["last_failure_time"] = time.monotonic()
    if _circuit["failure_count"] >= settings.SMS_PROVIDER_FAILURE_THRESHOLD:
        if not _circuit["open"]:
            log.error(
                "sms.circuit_breaker.open",
                failure_count=_circuit["failure_count"],
                threshold=settings.SMS_PROVIDER_FAILURE_THRESHOLD,
            )
        _circuit["open"] = True


def record_provider_success() -> None:
    """Reset failure counter on success."""
    _circuit["failure_count"] = 0
    _circuit["open"] = False

"""SMS provider factory with circuit-breaker fallback."""
import time

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


def _make_provider(name: str) -> BaseSmsProvider:
    if name == "tencent":
        from app.providers.tencent import TencentSmsProvider
        return TencentSmsProvider()
    if name == "chuanglan":
        from app.providers.chuanglan import ChuangLanSmsProvider
        return ChuangLanSmsProvider()
    from app.providers.aliyun import AliyunSmsProvider
    return AliyunSmsProvider()


def get_provider() -> BaseSmsProvider:
    """Return the active provider. Falls back to secondary if primary circuit is open."""
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

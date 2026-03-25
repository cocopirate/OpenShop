"""Tests for new sms-service features: masking, rate limiter, circuit breaker, providers."""
import os
import sys
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")


# ---------------------------------------------------------------------------
# Phone masking
# ---------------------------------------------------------------------------


def test_mask_phone_local():
    from app.core.masking import mask_phone

    assert mask_phone("13800001234") == "138****1234"


def test_mask_phone_e164():
    from app.core.masking import mask_phone

    result = mask_phone("+8613800001234")
    assert result.startswith("+86")
    assert "****" in result
    assert result.endswith("1234")


def test_mask_phone_short():
    from app.core.masking import mask_phone

    result = mask_phone("123")
    assert "****" in result


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limit_allows_first_request():
    from app.core.rate_limiter import check_rate_limit

    redis = AsyncMock()
    # Simulate pipeline: zremrangebyscore, zcard=0, zadd, expire
    pipe = MagicMock()
    pipe.zremrangebyscore = MagicMock()
    pipe.zcard = MagicMock()
    pipe.zadd = MagicMock()
    pipe.expire = MagicMock()
    pipe.execute = AsyncMock(return_value=[0, 0, 1, True])
    redis.pipeline = MagicMock(return_value=pipe)

    result = await check_rate_limit(redis, "test:key", limit=5, window=60)
    assert result.allowed is True
    assert result.remaining == 4
    assert result.retry_after == 0


@pytest.mark.asyncio
async def test_rate_limit_blocks_when_exceeded():
    from app.core.rate_limiter import check_rate_limit

    redis = AsyncMock()
    pipe = MagicMock()
    pipe.zremrangebyscore = MagicMock()
    pipe.zcard = MagicMock()
    pipe.zadd = MagicMock()
    pipe.expire = MagicMock()
    # count_before=5 (at limit)
    pipe.execute = AsyncMock(return_value=[0, 5, 1, True])
    redis.pipeline = MagicMock(return_value=pipe)

    oldest_ts = time.time() - 30
    redis.zrange = AsyncMock(return_value=[("entry", oldest_ts)])
    redis.zremrangebyscore = AsyncMock(return_value=1)

    result = await check_rate_limit(redis, "test:key", limit=5, window=60)
    assert result.allowed is False
    assert result.remaining == 0
    assert result.retry_after > 0


@pytest.mark.asyncio
async def test_check_phone_rate_limit_allowed():
    from app.core.rate_limiter import check_phone_rate_limit

    redis = AsyncMock()
    pipe = MagicMock()
    pipe.zremrangebyscore = MagicMock()
    pipe.zcard = MagicMock()
    pipe.zadd = MagicMock()
    pipe.expire = MagicMock()
    # Both minute and day limits not hit (count_before=0)
    pipe.execute = AsyncMock(return_value=[0, 0, 1, True])
    redis.pipeline = MagicMock(return_value=pipe)

    result = await check_phone_rate_limit(redis, "13800001234")
    assert result.allowed is True


# ---------------------------------------------------------------------------
# Circuit breaker (factory)
# ---------------------------------------------------------------------------


def test_circuit_breaker_opens_after_threshold():
    # Reset circuit state first
    import app.providers.factory as factory_mod
    factory_mod._circuit["failure_count"] = 0
    factory_mod._circuit["open"] = False
    factory_mod._circuit["last_failure_time"] = 0.0

    threshold = factory_mod.settings.SMS_PROVIDER_FAILURE_THRESHOLD
    for _ in range(threshold):
        factory_mod.record_provider_failure()

    assert factory_mod._circuit["open"] is True


def test_circuit_breaker_resets_on_success():
    import app.providers.factory as factory_mod
    factory_mod._circuit["failure_count"] = 5
    factory_mod._circuit["open"] = True

    factory_mod.record_provider_success()

    assert factory_mod._circuit["open"] is False
    assert factory_mod._circuit["failure_count"] == 0


def test_get_provider_returns_fallback_when_circuit_open():
    import app.providers.factory as factory_mod

    factory_mod._circuit["open"] = True
    factory_mod._circuit["last_failure_time"] = time.monotonic()  # just failed - won't recover yet

    with (
        patch.object(factory_mod.settings, "SMS_PROVIDER", "aliyun"),
        patch.object(factory_mod.settings, "SMS_PROVIDER_FALLBACK", "tencent"),
    ):
        provider = factory_mod.get_provider()
    from app.providers.tencent import TencentSmsProvider
    assert isinstance(provider, TencentSmsProvider)

    # cleanup
    factory_mod._circuit["open"] = False
    factory_mod._circuit["failure_count"] = 0


# ---------------------------------------------------------------------------
# ChuangLan provider
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chuanglan_send_success():
    from app.providers.chuanglan import ChuangLanSmsProvider

    provider = ChuangLanSmsProvider()
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value={"code": "0", "msgId": "MSG123"})

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await provider.send("13800001234", "tpl001", {"code": "123456"})

    assert result.success is True
    assert result.provider_message_id == "MSG123"


@pytest.mark.asyncio
async def test_chuanglan_send_failure():
    from app.providers.chuanglan import ChuangLanSmsProvider

    provider = ChuangLanSmsProvider()
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value={"code": "101", "errorMsg": "auth failed"})

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await provider.send("13800001234", "tpl001", {"code": "123456"})

    assert result.success is False
    assert result.error_code == "101"
    assert "auth failed" in result.error_message


@pytest.mark.asyncio
async def test_chuanglan_send_network_error():
    from app.providers.chuanglan import ChuangLanSmsProvider

    provider = ChuangLanSmsProvider()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("connection refused"))
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await provider.send("13800001234", "tpl001", {})

    assert result.success is False
    assert result.error_code == "NETWORK_ERROR"


@pytest.mark.asyncio
async def test_chuanglan_query_status_delivered():
    from app.providers.chuanglan import ChuangLanSmsProvider

    provider = ChuangLanSmsProvider()
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value={"code": "0", "reportCode": "DELIVRD"})

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await provider.query_status("MSG123")

    assert result.status == "DELIVERED"
    assert result.provider_message_id == "MSG123"


# ---------------------------------------------------------------------------
# Aliyun provider – error_code populated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_aliyun_send_populates_error_code():
    from app.providers.aliyun import AliyunSmsProvider

    provider = AliyunSmsProvider()
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(
        return_value={"Code": "isv.BUSINESS_LIMIT_CONTROL", "Message": "freq limit"}
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await provider.send("13800001234", "SMS_001", {"code": "123"})

    assert result.success is False
    assert result.error_code == "isv.BUSINESS_LIMIT_CONTROL"


# ---------------------------------------------------------------------------
# Tencent provider – error_code populated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tencent_send_populates_error_code():
    from app.providers.tencent import TencentSmsProvider

    provider = TencentSmsProvider()
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(
        return_value={
            "Response": {
                "SendStatusSet": [{"Code": "LimitExceeded", "Message": "freq limit", "SerialNo": ""}]
            }
        }
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await provider.send("13800001234", "123456", {"code": "111"})

    assert result.success is False
    assert result.error_code == "LimitExceeded"


# ---------------------------------------------------------------------------
# Config – new settings have sane defaults
# ---------------------------------------------------------------------------


def test_config_new_settings():
    from app.core.config import settings

    assert settings.ENV == "development"
    assert settings.SMS_PROVIDER_FAILURE_THRESHOLD == 3
    assert settings.SMS_PROVIDER_RECOVERY_TIMEOUT == 60
    assert settings.SMS_RECORDS_RETENTION_DAYS == 90
    assert settings.CHUANGLAN_ACCOUNT == ""
    assert settings.SMS_PROVIDER_FALLBACK == ""
    assert settings.OTEL_ENDPOINT == ""

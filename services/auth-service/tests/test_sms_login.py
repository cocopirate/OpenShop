"""Tests for auth-service SMS login / auto-register endpoint."""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Provide required env vars before importing app modules.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import app.main  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PHONE = "13800138000"
_CODE = "123456"
_CONSUMER_INT_ID = 42
_BIZ_ID = _CONSUMER_INT_ID
_TOKEN = "mock.jwt.token"


def _make_mock_engine(ok: bool = True):
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=None) if ok else AsyncMock(side_effect=Exception("db error"))
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=conn)
    cm.__aexit__ = AsyncMock(return_value=False)
    engine = MagicMock()
    engine.connect = MagicMock(return_value=cm)
    engine.dispose = AsyncMock()
    return engine


def _make_mock_redis(ok: bool = True):
    redis = AsyncMock()
    if ok:
        redis.ping = AsyncMock(return_value=True)
    else:
        redis.ping = AsyncMock(side_effect=Exception("redis error"))
    return redis


def _make_mock_credential(biz_id: int = _BIZ_ID, status: int = 1):
    cred = MagicMock()
    cred.biz_id = biz_id
    cred.status = status
    cred.identity = _PHONE
    cred.identity_type = 1
    cred.account_type = 1
    return cred


# ---------------------------------------------------------------------------
# POST /api/auth/consumer/sms-login tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sms_login_existing_user():
    """SMS login returns 200 + token for an existing registered consumer."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()

    with (
        patch("app.main.engine", mock_engine),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch("app.api.v1.auth.get_redis", return_value=mock_redis),
        patch(
            "app.api.v1.auth.login_or_register_consumer_by_sms",
            new_callable=AsyncMock,
            return_value=_TOKEN,
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/auth/consumer/sms-login",
                json={"phone": _PHONE, "code": _CODE},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["access_token"] == _TOKEN
    assert data["data"]["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_sms_login_new_user_auto_register():
    """SMS login auto-registers a new consumer and returns a token."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()

    with (
        patch("app.main.engine", mock_engine),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch("app.api.v1.auth.get_redis", return_value=mock_redis),
        patch(
            "app.api.v1.auth.login_or_register_consumer_by_sms",
            new_callable=AsyncMock,
            return_value=_TOKEN,
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/auth/consumer/sms-login",
                json={"phone": _PHONE, "code": _CODE},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["access_token"] == _TOKEN


@pytest.mark.asyncio
async def test_sms_login_invalid_code():
    """SMS login returns 422 when the verification code is invalid."""
    from fastapi import HTTPException, status
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()

    with (
        patch("app.main.engine", mock_engine),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch("app.api.v1.auth.get_redis", return_value=mock_redis),
        patch(
            "app.api.v1.auth.login_or_register_consumer_by_sms",
            new_callable=AsyncMock,
            side_effect=HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid or expired verification code",
            ),
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/auth/consumer/sms-login",
                json={"phone": _PHONE, "code": "000000"},
            )

    assert resp.status_code == 422
    data = resp.json()
    assert data["code"] != 0
    assert data["data"] is None


@pytest.mark.asyncio
async def test_sms_login_disabled_account():
    """SMS login returns 403 when the consumer account is disabled."""
    from fastapi import HTTPException, status
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()

    with (
        patch("app.main.engine", mock_engine),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch("app.api.v1.auth.get_redis", return_value=mock_redis),
        patch(
            "app.api.v1.auth.login_or_register_consumer_by_sms",
            new_callable=AsyncMock,
            side_effect=HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled",
            ),
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/auth/consumer/sms-login",
                json={"phone": _PHONE, "code": _CODE},
            )

    assert resp.status_code == 403
    data = resp.json()
    assert data["code"] != 0
    assert data["data"] is None


@pytest.mark.asyncio
async def test_sms_login_sms_service_unavailable():
    """SMS login returns 503 when the SMS service is unreachable."""
    from fastapi import HTTPException, status
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()

    with (
        patch("app.main.engine", mock_engine),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch("app.api.v1.auth.get_redis", return_value=mock_redis),
        patch(
            "app.api.v1.auth.login_or_register_consumer_by_sms",
            new_callable=AsyncMock,
            side_effect=HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="SMS service unavailable",
            ),
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/auth/consumer/sms-login",
                json={"phone": _PHONE, "code": _CODE},
            )

    assert resp.status_code == 503
    data = resp.json()
    assert data["code"] != 0
    assert data["data"] is None


@pytest.mark.asyncio
async def test_sms_login_missing_fields():
    """SMS login returns 422 when required fields are missing."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()

    with (
        patch("app.main.engine", mock_engine),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch("app.api.v1.auth.get_redis", return_value=mock_redis),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/auth/consumer/sms-login",
                json={"phone": _PHONE},  # missing 'code'
            )

    assert resp.status_code == 422

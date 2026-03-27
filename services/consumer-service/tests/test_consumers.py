"""Tests for consumer-service consumer endpoints."""
from __future__ import annotations

import os
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Provide required env vars before importing app modules.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import app.main  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CONSUMER_UUID = uuid.UUID("7c181d7b-4224-4189-9132-f9a8fc58a373")
_CONSUMER_INT_ID = 42


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


def _make_mock_consumer(
    public_id: uuid.UUID = _CONSUMER_UUID,
    nickname: str = "Alice",
    phone: str = "13800138000",
    email: str = "alice@example.com",
    points: int = 100,
    level: int = 1,
    status: int = 1,
):
    class _MockConsumer:
        pass

    c = _MockConsumer()
    c.id = _CONSUMER_INT_ID
    c.public_id = public_id
    c.nickname = nickname
    c.avatar_url = None
    c.phone = phone
    c.email = email
    c.gender = None
    c.birthday = None
    c.points = points
    c.level = level
    c.status = status
    c.created_at = datetime(2024, 1, 1, 0, 0, 0)
    return c


def _make_mock_address(consumer_id: int = _CONSUMER_INT_ID, addr_id: int = 1, is_default: int = 0):
    class _MockAddress:
        pass

    a = _MockAddress()
    a.id = addr_id
    a.consumer_id = consumer_id
    a.receiver = "Bob"
    a.phone = "13900139000"
    a.province = "Guangdong"
    a.city = "Shenzhen"
    a.district = "Nanshan"
    a.detail = "No.1 Science Park"
    a.is_default = is_default
    a.created_at = datetime(2024, 1, 1, 0, 0, 0)
    return a


# ---------------------------------------------------------------------------
# Consumer profile tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_consumer():
    """POST /api/consumers creates a consumer and returns 201."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()
    mock_consumer = _make_mock_consumer()

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.services.consumer_service.create_consumer",
            new_callable=AsyncMock,
            return_value=mock_consumer,
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/consumers",
                json={"nickname": "Alice", "phone": "13800138000", "email": "alice@example.com"},
            )

    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["nickname"] == "Alice"
    assert data["data"]["public_id"] == str(_CONSUMER_UUID)


@pytest.mark.asyncio
async def test_get_consumer_success():
    """GET /api/consumers/{id} returns consumer profile."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()
    mock_consumer = _make_mock_consumer()

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.services.consumer_service.get_consumer",
            new_callable=AsyncMock,
            return_value=mock_consumer,
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/consumers/{_CONSUMER_UUID}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["public_id"] == str(_CONSUMER_UUID)
    assert data["data"]["nickname"] == "Alice"
    assert data["data"]["points"] == 100


@pytest.mark.asyncio
async def test_get_consumer_not_found():
    """GET /api/consumers/{id} returns 404 when consumer does not exist."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.services.consumer_service.get_consumer",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/consumers/{_CONSUMER_UUID}")

    assert resp.status_code == 404
    data = resp.json()
    assert data["code"] != 0
    assert data["data"] is None


@pytest.mark.asyncio
async def test_update_consumer():
    """PUT /api/consumers/{id} updates consumer profile."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()
    mock_consumer = _make_mock_consumer(nickname="Bob")

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.services.consumer_service.update_consumer",
            new_callable=AsyncMock,
            return_value=mock_consumer,
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.put(
                f"/api/consumers/{_CONSUMER_UUID}",
                json={"nickname": "Bob"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["nickname"] == "Bob"


@pytest.mark.asyncio
async def test_get_points():
    """GET /api/consumers/{id}/points returns points balance."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()
    mock_consumer = _make_mock_consumer(points=500)

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.services.consumer_service.get_consumer",
            new_callable=AsyncMock,
            return_value=mock_consumer,
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/consumers/{_CONSUMER_UUID}/points")

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["points"] == 500


# ---------------------------------------------------------------------------
# Address tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_addresses():
    """GET /api/consumers/{id}/addresses returns address list."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()
    mock_consumer = _make_mock_consumer()
    mock_addresses = [_make_mock_address(addr_id=i) for i in range(1, 3)]

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.services.consumer_service.get_consumer",
            new_callable=AsyncMock,
            return_value=mock_consumer,
        ),
        patch(
            "app.services.address_service.list_addresses",
            new_callable=AsyncMock,
            return_value=mock_addresses,
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/consumers/{_CONSUMER_UUID}/addresses")

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 2


@pytest.mark.asyncio
async def test_create_address():
    """POST /api/consumers/{id}/addresses creates an address and returns 201."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()
    mock_consumer = _make_mock_consumer()
    mock_address = _make_mock_address()

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.services.consumer_service.get_consumer",
            new_callable=AsyncMock,
            return_value=mock_consumer,
        ),
        patch(
            "app.services.address_service.create_address",
            new_callable=AsyncMock,
            return_value=mock_address,
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/consumers/{_CONSUMER_UUID}/addresses",
                json={
                    "receiver": "Bob",
                    "phone": "13900139000",
                    "province": "Guangdong",
                    "city": "Shenzhen",
                    "district": "Nanshan",
                    "detail": "No.1 Science Park",
                },
            )

    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["receiver"] == "Bob"
    assert data["data"]["city"] == "Shenzhen"


@pytest.mark.asyncio
async def test_set_default_address():
    """POST /api/consumers/{id}/addresses/{addr_id}/set-default sets default address."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()
    mock_consumer = _make_mock_consumer()
    mock_address = _make_mock_address(is_default=1)

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.services.consumer_service.get_consumer",
            new_callable=AsyncMock,
            return_value=mock_consumer,
        ),
        patch(
            "app.services.address_service.set_default_address",
            new_callable=AsyncMock,
            return_value=mock_address,
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/consumers/{_CONSUMER_UUID}/addresses/1/set-default"
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["is_default"] == 1


# ---------------------------------------------------------------------------
# Internal endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_internal_get_consumer():
    """GET /internal/consumers/{id} returns minimal consumer info."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()
    mock_consumer = _make_mock_consumer()

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.services.consumer_service.get_consumer",
            new_callable=AsyncMock,
            return_value=mock_consumer,
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/internal/consumers/{_CONSUMER_UUID}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["id"] == _CONSUMER_INT_ID
    assert data["data"]["level"] == 1
    assert data["data"]["status"] == 1


@pytest.mark.asyncio
async def test_internal_adjust_points_add():
    """POST /internal/consumers/{id}/points adds points successfully."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()
    mock_consumer_before = _make_mock_consumer(points=100)
    mock_consumer_after = _make_mock_consumer(points=200)

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.services.consumer_service.get_consumer",
            new_callable=AsyncMock,
            return_value=mock_consumer_before,
        ),
        patch(
            "app.services.consumer_service.adjust_points",
            new_callable=AsyncMock,
            return_value=mock_consumer_after,
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/internal/consumers/{_CONSUMER_UUID}/points",
                json={"delta": 100, "reason": "order_complete", "ref_id": "ORD123"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["points"] == 200


@pytest.mark.asyncio
async def test_internal_adjust_points_insufficient():
    """POST /internal/consumers/{id}/points returns error when insufficient balance."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()
    mock_consumer = _make_mock_consumer(points=50)

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.services.consumer_service.get_consumer",
            new_callable=AsyncMock,
            return_value=mock_consumer,
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/internal/consumers/{_CONSUMER_UUID}/points",
                json={"delta": -100, "reason": "refund", "ref_id": "ORD456"},
            )

    assert resp.status_code == 422
    data = resp.json()
    assert data["code"] != 0
    assert data["data"] is None

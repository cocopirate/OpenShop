"""Unit tests for sms-service health endpoints and core config."""
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Provide required env vars before importing app modules.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_engine(ok: bool = True):
    """Return an async-context-manager mock that fakes engine.connect()."""
    conn = AsyncMock()
    if ok:
        conn.execute = AsyncMock(return_value=None)
    else:
        conn.execute = AsyncMock(side_effect=Exception("db error"))

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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_ok():
    """GET /health returns 200 with status=ok when DB and Redis are up."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine(ok=True)
    mock_redis = _make_mock_redis(ok=True)

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
    ):
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["checks"]["database"] == "ok"
    assert data["checks"]["redis"] == "ok"


@pytest.mark.asyncio
async def test_health_degraded_db():
    """GET /health returns degraded when DB is unreachable."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine(ok=False)
    mock_redis = _make_mock_redis(ok=True)

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
    ):
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["checks"]["database"] == "error"
    assert data["checks"]["redis"] == "ok"


@pytest.mark.asyncio
async def test_readiness_ok():
    """GET /health/ready returns 200 when both DB and Redis are up."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine(ok=True)
    mock_redis = _make_mock_redis(ok=True)

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
    ):
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/health/ready")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_readiness_db_fail():
    """GET /health/ready returns 503 when DB is unreachable."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine(ok=False)
    mock_redis = _make_mock_redis(ok=True)

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
    ):
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/health/ready")

    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_readiness_redis_fail():
    """GET /health/ready returns 503 when Redis is unreachable."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine(ok=True)
    mock_redis = _make_mock_redis(ok=False)

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
    ):
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/health/ready")

    assert resp.status_code == 503


def test_config_defaults():
    """Settings defaults are sensible and required env vars are loaded."""
    from app.core.config import settings

    assert settings.SERVICE_NAME == "sms-service"
    assert settings.SERVICE_PORT == 8010
    # Verify required infrastructure URLs are populated from env
    assert settings.DATABASE_URL, "DATABASE_URL must be set"
    assert settings.REDIS_URL, "REDIS_URL must be set"


"""Tests for user-service RBAC endpoints."""
from __future__ import annotations

import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Provide required env vars before importing app modules.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_engine(ok: bool = True):
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
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock(return_value=True)
        redis.incr = AsyncMock(return_value=1)
        redis.expire = AsyncMock(return_value=True)
    else:
        redis.ping = AsyncMock(side_effect=Exception("redis error"))
    return redis


def _make_mock_user(user_id: int = 1, username: str = "admin", status: str = "active"):
    """Create a mock admin user whose attributes serialize correctly via Pydantic."""

    class _MockAdminUser:
        pass

    user = _MockAdminUser()
    user.id = user_id
    user.username = username
    user.hashed_password = "$2b$12$placeholder"
    user.status = status  # plain string – AdminUserStatus is a str-enum so this works
    user.created_at = datetime(2024, 1, 1, 0, 0, 0)
    user.roles = []
    return user


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_success():
    """POST /api/auth/login returns token on valid credentials."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine(ok=True)
    mock_redis = _make_mock_redis(ok=True)
    mock_user = _make_mock_user()
    mock_db = AsyncMock()

    async def _override_get_db():
        yield mock_db

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.api.v1.auth.authenticate_user",
            new_callable=AsyncMock,
            return_value=mock_user,
        ),
        patch(
            "app.api.v1.auth.create_token_for_user",
            new_callable=AsyncMock,
            return_value="fake-jwt-token",
        ),
        patch("app.api.v1.auth.get_redis", return_value=mock_redis),
    ):
        from app.core.database import get_db
        from app.main import app

        app.dependency_overrides[get_db] = _override_get_db
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/login", json={"username": "admin", "password": "password"}
                )
        finally:
            app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_password():
    """POST /api/auth/login returns 401 on wrong password."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine(ok=True)
    mock_redis = _make_mock_redis(ok=True)
    mock_db = AsyncMock()

    async def _override_get_db():
        yield mock_db

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.api.v1.auth.authenticate_user",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch("app.api.v1.auth.get_redis", return_value=mock_redis),
    ):
        from app.core.database import get_db
        from app.main import app

        app.dependency_overrides[get_db] = _override_get_db
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/login", json={"username": "admin", "password": "wrong"}
                )
        finally:
            app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_user_not_found():
    """POST /api/auth/login returns 401 when user does not exist."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine(ok=True)
    mock_redis = _make_mock_redis(ok=True)
    mock_db = AsyncMock()

    async def _override_get_db():
        yield mock_db

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.api.v1.auth.authenticate_user",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch("app.api.v1.auth.get_redis", return_value=mock_redis),
    ):
        from app.core.database import get_db
        from app.main import app

        app.dependency_overrides[get_db] = _override_get_db
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/login",
                    json={"username": "nonexistent", "password": "password"},
                )
        finally:
            app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_user():
    """POST /api/users creates a user and returns 201."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine(ok=True)
    mock_redis = _make_mock_redis(ok=True)
    mock_user = _make_mock_user(user_id=1, username="newuser")

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.services.user_service.create_user",
            new_callable=AsyncMock,
            return_value=mock_user,
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/users", json={"username": "newuser", "password": "password123"}
            )

    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "newuser"


@pytest.mark.asyncio
async def test_get_users():
    """GET /api/users returns list of users."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine(ok=True)
    mock_redis = _make_mock_redis(ok=True)
    mock_users = [_make_mock_user(i, f"user{i}") for i in range(1, 4)]

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.services.user_service.get_users",
            new_callable=AsyncMock,
            return_value=mock_users,
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/users")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 3


@pytest.mark.asyncio
async def test_user_status_update():
    """POST /api/users/{id}/status updates user status."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine(ok=True)
    mock_redis = _make_mock_redis(ok=True)
    mock_user = _make_mock_user(user_id=1, username="admin", status="disabled")

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.services.user_service.update_user_status",
            new_callable=AsyncMock,
            return_value=mock_user,
        ),
        patch("app.api.v1.users.get_redis", return_value=mock_redis),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/users/1/status", json={"status": "disabled"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "disabled"


@pytest.mark.asyncio
async def test_assign_roles():
    """POST /api/users/{id}/roles assigns roles to user."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine(ok=True)
    mock_redis = _make_mock_redis(ok=True)
    mock_user = _make_mock_user(user_id=1, username="admin")

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.services.user_service.assign_roles_to_user",
            new_callable=AsyncMock,
            return_value=mock_user,
        ),
        patch("app.api.v1.users.get_redis", return_value=mock_redis),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/users/1/roles", json={"role_ids": [1, 2]})

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1

"""Tests for lead-service endpoints."""
from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Provide required env vars before importing app modules.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import app.main  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LEAD_UUID = uuid.UUID("a1b2c3d4-0000-0000-0000-000000000001")
_CONSUMER_UUID = uuid.UUID("a1b2c3d4-0000-0000-0000-000000000002")
_LOG_UUID = uuid.UUID("a1b2c3d4-0000-0000-0000-000000000003")


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


def _make_mock_lead(
    lead_id: uuid.UUID = _LEAD_UUID,
    phone: str = "13800138000",
    city: str = "上海",
    district: str = "浦东新区",
    product_ids: list[str] | None = None,
    status: str = "pending",
    source: str = "miniprogram",
    consumer_id: uuid.UUID | None = None,
    merchant_id: uuid.UUID | None = None,
    converted_order_id: uuid.UUID | None = None,
    remark: str | None = None,
) -> Any:
    class _MockLead:
        pass

    lead = _MockLead()
    lead.id = lead_id
    lead.phone = phone
    lead.city = city
    lead.district = district
    lead.product_ids = product_ids or ["prod-001", "prod-002"]
    lead.remark = remark
    lead.status = status
    lead.source = source
    lead.consumer_id = consumer_id
    lead.merchant_id = merchant_id
    lead.converted_order_id = converted_order_id
    lead.created_at = datetime(2026, 4, 4, 10, 0, 0)
    lead.updated_at = datetime(2026, 4, 4, 10, 0, 0)
    return lead


def _make_mock_log(log_id: uuid.UUID = _LOG_UUID, lead_id: uuid.UUID = _LEAD_UUID) -> Any:
    class _MockLog:
        pass

    entry = _MockLog()
    entry.id = log_id
    entry.lead_id = lead_id
    entry.from_status = "pending"
    entry.to_status = "converted"
    entry.operator_id = None
    entry.operator_type = "merchant"
    entry.note = "Test note"
    entry.created_at = datetime(2026, 4, 4, 10, 5, 0)
    return entry


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_lead():
    """POST /api/v1/leads creates a lead and returns 201."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()
    mock_lead = _make_mock_lead()

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.api.v1.leads._validate_product_ids",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.services.lead_service.create_lead",
            new_callable=AsyncMock,
            return_value=(mock_lead, True),
        ),
        patch(
            "app.api.v1.leads.publish_lead_submitted",
            new_callable=AsyncMock,
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/leads",
                json={
                    "phone": "13800138000",
                    "city": "上海",
                    "district": "浦东新区",
                    "product_ids": ["prod-001", "prod-002"],
                    "source": "miniprogram",
                },
            )

    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["id"] == str(_LEAD_UUID)
    assert data["data"]["status"] == "pending"


@pytest.mark.asyncio
async def test_create_lead_idempotent():
    """POST /api/v1/leads returns 200 for duplicate within 1 minute."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()
    mock_lead = _make_mock_lead()

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.api.v1.leads._validate_product_ids",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.services.lead_service.create_lead",
            new_callable=AsyncMock,
            return_value=(mock_lead, False),  # not created → idempotent
        ),
        patch(
            "app.api.v1.leads.publish_lead_submitted",
            new_callable=AsyncMock,
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/leads",
                json={
                    "phone": "13800138000",
                    "city": "上海",
                    "district": "浦东新区",
                    "product_ids": ["prod-001", "prod-002"],
                    "source": "miniprogram",
                },
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["id"] == str(_LEAD_UUID)


@pytest.mark.asyncio
async def test_get_lead_success():
    """GET /api/v1/leads/{id} returns lead details."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()
    mock_lead = _make_mock_lead()

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.services.lead_service.get_lead",
            new_callable=AsyncMock,
            return_value=mock_lead,
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/leads/{_LEAD_UUID}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["id"] == str(_LEAD_UUID)
    assert data["data"]["city"] == "上海"


@pytest.mark.asyncio
async def test_get_lead_not_found():
    """GET /api/v1/leads/{id} returns 404 when lead does not exist."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.services.lead_service.get_lead",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/leads/{_LEAD_UUID}")

    assert resp.status_code == 404
    data = resp.json()
    assert data["code"] != 0
    assert data["data"] is None


@pytest.mark.asyncio
async def test_list_leads_phone_masked():
    """GET /api/v1/leads returns masked phone numbers."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()
    mock_leads = [_make_mock_lead(phone="13800000000")]

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.services.lead_service.list_leads",
            new_callable=AsyncMock,
            return_value=(mock_leads, 1),
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/leads")

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["total"] == 1
    phone = data["data"]["items"][0]["phone"]
    assert "****" in phone
    assert phone == "138****0000"


@pytest.mark.asyncio
async def test_cancel_lead():
    """PATCH /api/v1/leads/{id}/cancel cancels a pending lead."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()
    mock_lead = _make_mock_lead(status="cancelled")

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.services.lead_service.cancel_lead",
            new_callable=AsyncMock,
            return_value=mock_lead,
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.patch(
                f"/api/v1/leads/{_LEAD_UUID}/cancel",
                json={"note": "用户主动取消"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_lead_already_terminal():
    """PATCH /api/v1/leads/{id}/cancel returns 409 for terminal lead."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.services.lead_service.cancel_lead",
            new_callable=AsyncMock,
            side_effect=ValueError("Lead is already in terminal status: converted"),
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.patch(f"/api/v1/leads/{_LEAD_UUID}/cancel", json={})

    assert resp.status_code == 409
    data = resp.json()
    assert data["code"] != 0


@pytest.mark.asyncio
async def test_convert_lead():
    """PATCH /api/v1/leads/{id}/convert marks lead as converted."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()
    mock_lead = _make_mock_lead(status="converted")

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.services.lead_service.convert_lead",
            new_callable=AsyncMock,
            return_value=mock_lead,
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.patch(
                f"/api/v1/leads/{_LEAD_UUID}/convert",
                json={"note": "已电话沟通，用户确认下单"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["status"] == "converted"


@pytest.mark.asyncio
async def test_get_lead_logs():
    """GET /api/v1/leads/{id}/logs returns status change logs."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()
    mock_lead = _make_mock_lead()
    mock_logs = [_make_mock_log()]

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
        patch(
            "app.services.lead_service.get_lead",
            new_callable=AsyncMock,
            return_value=mock_lead,
        ),
        patch(
            "app.services.lead_service.get_lead_logs",
            new_callable=AsyncMock,
            return_value=mock_logs,
        ),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/leads/{_LEAD_UUID}/logs")

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 1
    assert data["data"][0]["to_status"] == "converted"


@pytest.mark.asyncio
async def test_health_check():
    """GET /health returns service health status."""
    from httpx import ASGITransport, AsyncClient

    mock_engine = _make_mock_engine()
    mock_redis = _make_mock_redis()

    with (
        patch("app.main.engine", mock_engine),
        patch("app.main.get_redis", return_value=mock_redis),
        patch("app.core.redis.init_redis", new_callable=AsyncMock),
        patch("app.core.redis.close_redis", new_callable=AsyncMock),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "lead-service"
    assert data["status"] in ("ok", "degraded")

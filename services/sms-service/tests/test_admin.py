"""Unit tests for admin SMS service functions and admin router endpoints."""
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")


# ---------------------------------------------------------------------------
# Admin service – template CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_templates_returns_all():
    from app.services.admin_service import list_templates

    mock_db = AsyncMock()

    # total count query
    count_result = MagicMock()
    count_result.scalar_one.return_value = 2

    # rows query
    tpl1 = MagicMock()
    tpl1.id = 1
    tpl2 = MagicMock()
    tpl2.id = 2
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = [tpl1, tpl2]

    mock_db.execute = AsyncMock(side_effect=[count_result, rows_result])

    templates, total = await list_templates(mock_db)
    assert total == 2
    assert len(templates) == 2


@pytest.mark.asyncio
async def test_get_template_found():
    from app.services.admin_service import get_template

    mock_db = AsyncMock()
    mock_tpl = MagicMock()
    mock_tpl.id = 42
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_tpl
    mock_db.execute = AsyncMock(return_value=result)

    tpl = await get_template(mock_db, 42)
    assert tpl is not None
    assert tpl.id == 42


@pytest.mark.asyncio
async def test_get_template_not_found():
    from app.services.admin_service import get_template

    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result)

    tpl = await get_template(mock_db, 999)
    assert tpl is None


@pytest.mark.asyncio
async def test_create_template():
    from app.schemas.sms import SmsTemplateCreate
    from app.services.admin_service import create_template

    mock_db = AsyncMock()

    data = SmsTemplateCreate(
        provider_template_id="SMS_001",
        name="登录验证码",
        content="您的验证码是 ${code}，5 分钟内有效。",
        provider="aliyun",
        is_active=True,
    )

    created = await create_template(mock_db, data)
    mock_db.add.assert_called_once()
    mock_db.flush.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()
    assert created is not None


@pytest.mark.asyncio
async def test_update_template_not_found():
    from app.schemas.sms import SmsTemplateUpdate
    from app.services.admin_service import update_template

    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result)

    updated = await update_template(mock_db, 999, SmsTemplateUpdate(name="new name"))
    assert updated is None


@pytest.mark.asyncio
async def test_update_template_success():
    from app.schemas.sms import SmsTemplateUpdate
    from app.services.admin_service import update_template

    mock_db = AsyncMock()
    mock_tpl = MagicMock()
    mock_tpl.id = 1
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_tpl
    mock_db.execute = AsyncMock(return_value=result)

    updated = await update_template(mock_db, 1, SmsTemplateUpdate(name="new name", is_active=False))
    assert updated is not None
    assert mock_tpl.name == "new name"
    assert mock_tpl.is_active is False


@pytest.mark.asyncio
async def test_delete_template_not_found():
    from app.services.admin_service import delete_template

    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result)

    deleted = await delete_template(mock_db, 999)
    assert deleted is False


@pytest.mark.asyncio
async def test_delete_template_success():
    from app.services.admin_service import delete_template

    mock_db = AsyncMock()
    mock_tpl = MagicMock()
    mock_tpl.id = 1
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_tpl
    mock_db.execute = AsyncMock(return_value=result)

    deleted = await delete_template(mock_db, 1)
    assert deleted is True
    mock_db.delete.assert_awaited_once_with(mock_tpl)


# ---------------------------------------------------------------------------
# Admin service – records
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_record_not_found():
    from app.services.admin_service import delete_record

    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result)

    deleted = await delete_record(mock_db, 999)
    assert deleted is False


@pytest.mark.asyncio
async def test_delete_record_success():
    from app.services.admin_service import delete_record

    mock_db = AsyncMock()
    mock_record = MagicMock()
    mock_record.id = 1
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_record
    mock_db.execute = AsyncMock(return_value=result)

    deleted = await delete_record(mock_db, 1)
    assert deleted is True
    mock_db.delete.assert_awaited_once_with(mock_record)


# ---------------------------------------------------------------------------
# Admin service – configuration
# ---------------------------------------------------------------------------


def test_get_sms_config_returns_expected_keys():
    from app.services.admin_service import get_sms_config

    config = get_sms_config()
    expected_keys = {
        "sms_provider",
        "sms_provider_fallback",
        "sms_provider_failure_threshold",
        "sms_provider_recovery_timeout",
        "sms_code_ttl",
        "sms_rate_limit_phone_per_minute",
        "sms_rate_limit_phone_per_day",
        "sms_rate_limit_ip_per_minute",
        "sms_rate_limit_ip_per_day",
        "sms_records_retention_days",
    }
    assert expected_keys.issubset(set(config.keys()))
    # Provider credential blocks are also present
    assert "chuanglan" in config
    assert "aliyun" in config
    assert "aliyun_phone_svc" in config
    assert "tencent" in config


def _make_config_mock_db():
    """AsyncMock db that satisfies _persist_config (no existing store row)."""
    mock_db = AsyncMock()
    store_result = MagicMock()
    store_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=store_result)
    return mock_db


@pytest.mark.asyncio
async def test_update_sms_config_partial():
    from app.core.config import settings
    from app.schemas.sms import SmsConfigUpdate
    from app.services.admin_service import update_sms_config

    original_ttl = settings.SMS_CODE_TTL
    mock_db = _make_config_mock_db()
    try:
        result = await update_sms_config(SmsConfigUpdate(sms_code_ttl=600), mock_db)
        assert result["sms_code_ttl"] == 600
        assert settings.SMS_CODE_TTL == 600
    finally:
        settings.SMS_CODE_TTL = original_ttl


@pytest.mark.asyncio
async def test_update_sms_config_provider():
    from app.core.config import settings
    from app.schemas.sms import SmsConfigUpdate
    from app.services.admin_service import update_sms_config

    original_provider = settings.SMS_PROVIDER
    mock_db = _make_config_mock_db()
    try:
        result = await update_sms_config(SmsConfigUpdate(sms_provider="tencent"), mock_db)
        assert result["sms_provider"] == "tencent"
        assert settings.SMS_PROVIDER == "tencent"
    finally:
        settings.SMS_PROVIDER = original_provider


@pytest.mark.asyncio
async def test_update_sms_config_provider_credentials():
    """PUT /api/sms/config updates aliyun_phone_svc credentials in settings."""
    from app.core.config import settings
    from app.schemas.sms import AliyunCredentialsUpdate, SmsConfigUpdate
    from app.services.admin_service import update_sms_config

    original_key = settings.ALIYUN_PHONE_SVC_ACCESS_KEY_ID
    mock_db = _make_config_mock_db()
    try:
        result = await update_sms_config(
            SmsConfigUpdate(aliyun_phone_svc=AliyunCredentialsUpdate(access_key_id="new-key")),
            mock_db,
        )
        assert settings.ALIYUN_PHONE_SVC_ACCESS_KEY_ID == "new-key"
        assert result["aliyun_phone_svc"]["access_key_id"] == "new-key"
    finally:
        settings.ALIYUN_PHONE_SVC_ACCESS_KEY_ID = original_key


# ---------------------------------------------------------------------------
# Admin router – HTTP endpoint smoke tests
# ---------------------------------------------------------------------------


def _make_app():
    """Create a minimal FastAPI app with the standard SMS router for testing."""
    from fastapi import FastAPI
    from app.api.v1.router import router

    app = FastAPI()
    app.include_router(router, prefix="/api/sms")
    return app


@pytest.mark.asyncio
async def test_admin_get_config_endpoint():
    from httpx import ASGITransport, AsyncClient

    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/sms/config")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "sms_provider" in data
    assert "sms_code_ttl" in data


@pytest.mark.asyncio
async def test_admin_update_config_endpoint():
    from app.core.config import settings
    from app.core.database import get_db
    from httpx import ASGITransport, AsyncClient

    original_ttl = settings.SMS_CODE_TTL
    app = _make_app()

    async def _override_db():
        mock_db = AsyncMock()
        store_result = MagicMock()
        store_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=store_result)
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.put("/api/sms/config", json={"sms_code_ttl": 120})
        assert resp.status_code == 200
        assert resp.json()["data"]["sms_code_ttl"] == 120
    finally:
        settings.SMS_CODE_TTL = original_ttl


@pytest.mark.asyncio
async def test_admin_delete_record_not_found():
    from httpx import ASGITransport, AsyncClient

    app = _make_app()

    async def _override_db():
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)
        yield mock_db

    from app.core.database import get_db
    app.dependency_overrides[get_db] = _override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete("/api/sms/records/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_delete_template_not_found():
    from httpx import ASGITransport, AsyncClient

    app = _make_app()

    async def _override_db():
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)
        yield mock_db

    from app.core.database import get_db
    app.dependency_overrides[get_db] = _override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete("/api/sms/templates/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_get_template_not_found():
    from httpx import ASGITransport, AsyncClient

    app = _make_app()

    async def _override_db():
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)
        yield mock_db

    from app.core.database import get_db
    app.dependency_overrides[get_db] = _override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/sms/templates/9999")
    assert resp.status_code == 404

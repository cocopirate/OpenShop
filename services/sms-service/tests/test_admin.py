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
        "sms_default_channel",
        "sms_code_ttl",
        "sms_rate_limit_phone_per_minute",
        "sms_rate_limit_phone_per_day",
        "sms_rate_limit_ip_per_minute",
        "sms_rate_limit_ip_per_day",
        "sms_records_retention_days",
        "sms_channels",
        "sms_client_keys",
    }
    assert expected_keys == set(config.keys())


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
async def test_update_sms_config_default_channel():
    from app.core.config import settings
    from app.schemas.sms import SmsConfigUpdate
    from app.services.admin_service import update_sms_config

    original = settings.SMS_DEFAULT_CHANNEL
    mock_db = _make_config_mock_db()
    try:
        result = await update_sms_config(SmsConfigUpdate(sms_default_channel="internal"), mock_db)
        assert result["sms_default_channel"] == "internal"
        assert settings.SMS_DEFAULT_CHANNEL == "internal"
    finally:
        settings.SMS_DEFAULT_CHANNEL = original


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
    assert "sms_default_channel" in data
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


# ---------------------------------------------------------------------------
# Admin service – Channel CRUD
# ---------------------------------------------------------------------------


def _make_persist_db():
    """AsyncMock db that satisfies _persist_config (no existing store row)."""
    mock_db = AsyncMock()
    store_result = MagicMock()
    store_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=store_result)
    return mock_db


def test_list_channels_empty():
    from app.core.config import settings
    from app.services.admin_service import list_channels

    original = settings.SMS_CHANNELS
    settings.SMS_CHANNELS = {}
    try:
        items, total = list_channels()
        assert total == 0
        assert items == []
    finally:
        settings.SMS_CHANNELS = original


def test_list_channels_with_data():
    from app.core.config import settings
    from app.services.admin_service import list_channels

    original = settings.SMS_CHANNELS
    settings.SMS_CHANNELS = {
        "biz_a": {
            "provider": "aliyun",
            "access_key_id": "k1",
            "access_key_secret": "s1",
            "sign_name": "A",
        }
    }
    try:
        items, total = list_channels()
        assert total == 1
        assert items[0].name == "biz_a"
        assert items[0].access_key_secret == "***"  # masked
    finally:
        settings.SMS_CHANNELS = original


def test_get_channel_not_found():
    from app.core.config import settings
    from app.services.admin_service import get_channel

    original = settings.SMS_CHANNELS
    settings.SMS_CHANNELS = {}
    try:
        result = get_channel("nonexistent")
        assert result is None
    finally:
        settings.SMS_CHANNELS = original


def test_get_channel_found():
    from app.core.config import settings
    from app.services.admin_service import get_channel

    original = settings.SMS_CHANNELS
    settings.SMS_CHANNELS = {
        "biz_b": {"provider": "tencent", "secret_id": "id1", "secret_key": "sk1"}
    }
    try:
        ch = get_channel("biz_b")
        assert ch is not None
        assert ch.provider == "tencent"
        assert ch.secret_key == "***"
    finally:
        settings.SMS_CHANNELS = original


@pytest.mark.asyncio
async def test_upsert_channel():
    from app.core.config import settings
    from app.schemas.sms import SmsChannelCreate
    from app.services.admin_service import upsert_channel

    original = settings.SMS_CHANNELS
    settings.SMS_CHANNELS = {}
    mock_db = _make_persist_db()
    try:
        data = SmsChannelCreate(provider="aliyun", access_key_id="k", access_key_secret="s")
        ch = await upsert_channel("new_biz", data, mock_db)
        assert ch.name == "new_biz"
        assert ch.provider == "aliyun"
        assert ch.access_key_secret == "***"
        assert "new_biz" in settings.SMS_CHANNELS
    finally:
        settings.SMS_CHANNELS = original


@pytest.mark.asyncio
async def test_patch_channel_not_found():
    from app.core.config import settings
    from app.schemas.sms import SmsChannelUpdate
    from app.services.admin_service import patch_channel

    original = settings.SMS_CHANNELS
    settings.SMS_CHANNELS = {}
    mock_db = _make_persist_db()
    try:
        result = await patch_channel("ghost", SmsChannelUpdate(sign_name="X"), mock_db)
        assert result is None
    finally:
        settings.SMS_CHANNELS = original


@pytest.mark.asyncio
async def test_patch_channel_success():
    from app.core.config import settings
    from app.schemas.sms import SmsChannelUpdate
    from app.services.admin_service import patch_channel

    original = settings.SMS_CHANNELS
    settings.SMS_CHANNELS = {"biz_c": {"provider": "aliyun", "sign_name": "old"}}
    mock_db = _make_persist_db()
    try:
        result = await patch_channel("biz_c", SmsChannelUpdate(sign_name="new"), mock_db)
        assert result is not None
        assert settings.SMS_CHANNELS["biz_c"]["sign_name"] == "new"
        assert settings.SMS_CHANNELS["biz_c"]["provider"] == "aliyun"
    finally:
        settings.SMS_CHANNELS = original


@pytest.mark.asyncio
async def test_delete_channel_not_found():
    from app.core.config import settings
    from app.services.admin_service import delete_channel

    original = settings.SMS_CHANNELS
    settings.SMS_CHANNELS = {}
    mock_db = _make_persist_db()
    try:
        ok = await delete_channel("ghost", mock_db)
        assert ok is False
    finally:
        settings.SMS_CHANNELS = original


@pytest.mark.asyncio
async def test_delete_channel_success():
    from app.core.config import settings
    from app.services.admin_service import delete_channel

    original = settings.SMS_CHANNELS
    settings.SMS_CHANNELS = {"biz_d": {"provider": "chuanglan"}}
    mock_db = _make_persist_db()
    try:
        ok = await delete_channel("biz_d", mock_db)
        assert ok is True
        assert "biz_d" not in settings.SMS_CHANNELS
    finally:
        settings.SMS_CHANNELS = original


# ---------------------------------------------------------------------------
# Admin service – Client Key CRUD
# ---------------------------------------------------------------------------


def test_list_client_keys_empty():
    from app.core.config import settings
    from app.services.admin_service import list_client_keys

    original = settings.SMS_CLIENT_KEYS
    settings.SMS_CLIENT_KEYS = {}
    try:
        items, total = list_client_keys()
        assert total == 0
    finally:
        settings.SMS_CLIENT_KEYS = original


def test_list_client_keys_with_data():
    from app.core.config import settings
    from app.services.admin_service import list_client_keys

    original = settings.SMS_CLIENT_KEYS
    settings.SMS_CLIENT_KEYS = {"key-abc": "biz_a", "key-xyz": "biz_b"}
    try:
        items, total = list_client_keys()
        assert total == 2
        assert {i.api_key for i in items} == {"key-abc", "key-xyz"}
    finally:
        settings.SMS_CLIENT_KEYS = original


@pytest.mark.asyncio
async def test_create_client_key():
    from app.core.config import settings
    from app.schemas.sms import SmsClientKeyCreate
    from app.services.admin_service import create_client_key

    original = settings.SMS_CLIENT_KEYS
    settings.SMS_CLIENT_KEYS = {}
    mock_db = _make_persist_db()
    try:
        k = await create_client_key(SmsClientKeyCreate(api_key="new-key", channel="biz_a"), mock_db)
        assert k.api_key == "new-key"
        assert k.channel == "biz_a"
        assert settings.SMS_CLIENT_KEYS["new-key"] == "biz_a"
    finally:
        settings.SMS_CLIENT_KEYS = original


@pytest.mark.asyncio
async def test_delete_client_key_not_found():
    from app.core.config import settings
    from app.services.admin_service import delete_client_key

    original = settings.SMS_CLIENT_KEYS
    settings.SMS_CLIENT_KEYS = {}
    mock_db = _make_persist_db()
    try:
        ok = await delete_client_key("ghost-key", mock_db)
        assert ok is False
    finally:
        settings.SMS_CLIENT_KEYS = original


@pytest.mark.asyncio
async def test_delete_client_key_success():
    from app.core.config import settings
    from app.services.admin_service import delete_client_key

    original = settings.SMS_CLIENT_KEYS
    settings.SMS_CLIENT_KEYS = {"del-key": "biz_a"}
    mock_db = _make_persist_db()
    try:
        ok = await delete_client_key("del-key", mock_db)
        assert ok is True
        assert "del-key" not in settings.SMS_CLIENT_KEYS
    finally:
        settings.SMS_CLIENT_KEYS = original


# ---------------------------------------------------------------------------
# Admin router – Channel / Client-key HTTP endpoint smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_channels_endpoint_empty():
    from app.core.config import settings
    from httpx import ASGITransport, AsyncClient

    original = settings.SMS_CHANNELS
    settings.SMS_CHANNELS = {}
    app = _make_app()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/sms/channels")
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 0
    finally:
        settings.SMS_CHANNELS = original


@pytest.mark.asyncio
async def test_get_channel_endpoint_not_found():
    from app.core.config import settings
    from httpx import ASGITransport, AsyncClient

    original = settings.SMS_CHANNELS
    settings.SMS_CHANNELS = {}
    app = _make_app()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/sms/channels/ghost")
        assert resp.status_code == 404
    finally:
        settings.SMS_CHANNELS = original


@pytest.mark.asyncio
async def test_upsert_channel_endpoint():
    from app.core.config import settings
    from app.core.database import get_db
    from httpx import ASGITransport, AsyncClient

    original = settings.SMS_CHANNELS
    settings.SMS_CHANNELS = {}
    app = _make_app()

    async def _override_db():
        yield _make_persist_db()

    app.dependency_overrides[get_db] = _override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.put(
                "/api/sms/channels/biz_test",
                json={"provider": "aliyun", "access_key_id": "k1", "access_key_secret": "s1"},
            )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["name"] == "biz_test"
        assert data["access_key_secret"] == "***"
        assert "biz_test" in settings.SMS_CHANNELS
    finally:
        settings.SMS_CHANNELS = original


@pytest.mark.asyncio
async def test_delete_channel_endpoint_not_found():
    from app.core.config import settings
    from app.core.database import get_db
    from httpx import ASGITransport, AsyncClient

    original = settings.SMS_CHANNELS
    settings.SMS_CHANNELS = {}
    app = _make_app()

    async def _override_db():
        yield _make_persist_db()

    app.dependency_overrides[get_db] = _override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete("/api/sms/channels/ghost")
        assert resp.status_code == 404
    finally:
        settings.SMS_CHANNELS = original


@pytest.mark.asyncio
async def test_list_client_keys_endpoint():
    from app.core.config import settings
    from httpx import ASGITransport, AsyncClient

    original = settings.SMS_CLIENT_KEYS
    settings.SMS_CLIENT_KEYS = {"k1": "biz_a"}
    app = _make_app()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/sms/client-keys")
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 1
    finally:
        settings.SMS_CLIENT_KEYS = original


@pytest.mark.asyncio
async def test_create_client_key_endpoint():
    from app.core.config import settings
    from app.core.database import get_db
    from httpx import ASGITransport, AsyncClient

    original = settings.SMS_CLIENT_KEYS
    settings.SMS_CLIENT_KEYS = {}
    app = _make_app()

    async def _override_db():
        yield _make_persist_db()

    app.dependency_overrides[get_db] = _override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/sms/client-keys",
                json={"api_key": "test-key-001", "channel": "biz_a"},
            )
        assert resp.status_code == 201
        assert resp.json()["data"]["channel"] == "biz_a"
    finally:
        settings.SMS_CLIENT_KEYS = original


@pytest.mark.asyncio
async def test_delete_client_key_endpoint_not_found():
    from app.core.config import settings
    from app.core.database import get_db
    from httpx import ASGITransport, AsyncClient

    original = settings.SMS_CLIENT_KEYS
    settings.SMS_CLIENT_KEYS = {}
    app = _make_app()

    async def _override_db():
        yield _make_persist_db()

    app.dependency_overrides[get_db] = _override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete("/api/sms/client-keys/ghost-key")
        assert resp.status_code == 404
    finally:
        settings.SMS_CLIENT_KEYS = original

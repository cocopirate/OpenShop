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
# Admin service – Policy CRUD
# ---------------------------------------------------------------------------


def _make_db_no_rows():
    """AsyncMock db that returns None for scalar_one_or_none and 0 for scalar_one."""
    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    result.scalar_one.return_value = 0
    result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=result)
    return mock_db


@pytest.mark.asyncio
async def test_list_policies_empty():
    from app.services.admin_service import list_policies

    mock_db = AsyncMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(side_effect=[count_result, rows_result])

    items, total = await list_policies(mock_db)
    assert total == 0
    assert items == []


@pytest.mark.asyncio
async def test_get_policy_not_found():
    from app.services.admin_service import get_policy

    mock_db = _make_db_no_rows()
    result = await get_policy(mock_db, "nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_upsert_policy_creates_new():
    from app.schemas.sms import SmsPolicyCreate
    from app.services.admin_service import upsert_policy

    mock_db = AsyncMock()
    # get_policy returns None (not found)
    not_found = MagicMock()
    not_found.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=not_found)

    data = SmsPolicyCreate()
    policy = await upsert_policy(mock_db, "test_policy", data)
    mock_db.add.assert_called_once()
    mock_db.flush.assert_awaited_once()
    assert policy is not None


@pytest.mark.asyncio
async def test_delete_policy_not_found():
    from app.services.admin_service import delete_policy

    mock_db = _make_db_no_rows()
    deleted, in_use = await delete_policy(mock_db, "ghost")
    assert deleted is False
    assert in_use is False


@pytest.mark.asyncio
async def test_delete_policy_in_use():
    from app.services.admin_service import delete_policy

    mock_db = AsyncMock()
    # First execute: get_policy – returns a mock policy
    mock_policy = MagicMock()
    policy_result = MagicMock()
    policy_result.scalar_one_or_none.return_value = mock_policy
    # Second execute: count channels using policy – returns 1
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1
    mock_db.execute = AsyncMock(side_effect=[policy_result, count_result])

    deleted, in_use = await delete_policy(mock_db, "in_use_policy")
    assert deleted is False
    assert in_use is True


# ---------------------------------------------------------------------------
# Admin service – Channel CRUD (DB-backed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_channels_empty():
    from app.services.admin_service import list_channels

    mock_db = AsyncMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(side_effect=[count_result, rows_result])

    items, total = await list_channels(mock_db)
    assert total == 0
    assert items == []


@pytest.mark.asyncio
async def test_get_channel_not_found():
    from app.services.admin_service import get_channel

    mock_db = _make_db_no_rows()
    result = await get_channel(mock_db, "nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_get_channel_found():
    from app.models.sms_channel import SmsChannel
    from app.services.admin_service import get_channel

    mock_db = AsyncMock()
    mock_ch = SmsChannel(
        name="biz_b",
        provider="tencent",
        secret_id="id1",
        secret_key="sk1",
        is_default=False,
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_ch
    mock_db.execute = AsyncMock(return_value=result)

    ch = await get_channel(mock_db, "biz_b")
    assert ch is not None
    assert ch.provider == "tencent"
    assert ch.secret_key == "***"  # masked


@pytest.mark.asyncio
async def test_upsert_channel_creates_new():
    from app.schemas.sms import SmsChannelCreate
    from app.services.admin_service import upsert_channel

    mock_db = AsyncMock()
    # get_channel_raw returns None (channel not found)
    not_found = MagicMock()
    not_found.scalar_one_or_none.return_value = None
    # is_default=False so no clear query needed; only one execute call
    mock_db.execute = AsyncMock(return_value=not_found)

    data = SmsChannelCreate(provider="aliyun", access_key_id="k", access_key_secret="s")
    ch = await upsert_channel(mock_db, "new_biz", data)
    mock_db.add.assert_called_once()
    mock_db.flush.assert_awaited_once()
    assert ch is not None
    assert ch.provider == "aliyun"
    assert ch.access_key_secret == "***"


@pytest.mark.asyncio
async def test_patch_channel_not_found():
    from app.schemas.sms import SmsChannelUpdate
    from app.services.admin_service import patch_channel

    mock_db = _make_db_no_rows()
    result = await patch_channel(mock_db, "ghost", SmsChannelUpdate(sign_name="X"))
    assert result is None


@pytest.mark.asyncio
async def test_delete_channel_not_found():
    from app.services.admin_service import delete_channel

    mock_db = _make_db_no_rows()
    ok = await delete_channel(mock_db, "ghost")
    assert ok is False


@pytest.mark.asyncio
async def test_delete_channel_success():
    from app.models.sms_channel import SmsChannel
    from app.services.admin_service import delete_channel

    mock_db = AsyncMock()
    mock_ch = SmsChannel(name="biz_d", provider="chuanglan", is_default=False)
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_ch
    mock_db.execute = AsyncMock(return_value=result)

    ok = await delete_channel(mock_db, "biz_d")
    assert ok is True
    mock_db.delete.assert_awaited_once_with(mock_ch)


# ---------------------------------------------------------------------------
# Admin service – Client Key CRUD (DB-backed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_client_keys_empty():
    from app.services.admin_service import list_client_keys

    mock_db = AsyncMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(side_effect=[count_result, rows_result])

    items, total = await list_client_keys(mock_db)
    assert total == 0
    assert items == []


@pytest.mark.asyncio
async def test_list_client_keys_with_data():
    from app.models.sms_client_key import SmsClientKey
    from app.services.admin_service import list_client_keys

    mock_db = AsyncMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = 2
    k1 = SmsClientKey(api_key="key-abc", channel="biz_a")
    k2 = SmsClientKey(api_key="key-xyz", channel="biz_b")
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = [k1, k2]
    mock_db.execute = AsyncMock(side_effect=[count_result, rows_result])

    items, total = await list_client_keys(mock_db)
    assert total == 2
    assert {i.api_key for i in items} == {"key-abc", "key-xyz"}


@pytest.mark.asyncio
async def test_create_client_key():
    from app.schemas.sms import SmsClientKeyCreate
    from app.services.admin_service import create_client_key

    mock_db = AsyncMock()
    # get existing key returns None (new)
    not_found = MagicMock()
    not_found.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=not_found)

    k = await create_client_key(mock_db, SmsClientKeyCreate(api_key="new-key", channel="biz_a"))
    assert k.api_key == "new-key"
    assert k.channel == "biz_a"
    mock_db.add.assert_called_once()


@pytest.mark.asyncio
async def test_delete_client_key_not_found():
    from app.services.admin_service import delete_client_key

    mock_db = _make_db_no_rows()
    ok = await delete_client_key(mock_db, "ghost-key")
    assert ok is False


@pytest.mark.asyncio
async def test_delete_client_key_success():
    from app.models.sms_client_key import SmsClientKey
    from app.services.admin_service import delete_client_key

    mock_db = AsyncMock()
    mock_key = SmsClientKey(api_key="del-key", channel="biz_a")
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_key
    mock_db.execute = AsyncMock(return_value=result)

    ok = await delete_client_key(mock_db, "del-key")
    assert ok is True
    mock_db.delete.assert_awaited_once_with(mock_key)


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


def _make_db_override(execute_side_effects=None, execute_return=None):
    """Return an async generator that yields a mocked DB session."""
    async def _override():
        mock_db = AsyncMock()
        if execute_side_effects:
            mock_db.execute = AsyncMock(side_effect=execute_side_effects)
        elif execute_return is not None:
            mock_db.execute = AsyncMock(return_value=execute_return)
        else:
            result = MagicMock()
            result.scalar_one_or_none.return_value = None
            result.scalar_one.return_value = 0
            result.scalars.return_value.all.return_value = []
            mock_db.execute = AsyncMock(return_value=result)
        yield mock_db
    return _override


@pytest.mark.asyncio
async def test_admin_delete_record_not_found():
    from httpx import ASGITransport, AsyncClient

    app = _make_app()
    from app.core.database import get_db
    app.dependency_overrides[get_db] = _make_db_override()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete("/api/sms/records/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_delete_template_not_found():
    from httpx import ASGITransport, AsyncClient

    app = _make_app()
    from app.core.database import get_db
    app.dependency_overrides[get_db] = _make_db_override()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete("/api/sms/templates/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_get_template_not_found():
    from httpx import ASGITransport, AsyncClient

    app = _make_app()
    from app.core.database import get_db
    app.dependency_overrides[get_db] = _make_db_override()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/sms/templates/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_channels_endpoint_empty():
    from httpx import ASGITransport, AsyncClient

    app = _make_app()

    from app.core.database import get_db
    # Two execute calls: count=0, rows=[]
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = []
    app.dependency_overrides[get_db] = _make_db_override(
        execute_side_effects=[count_result, rows_result]
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/sms/channels")
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_get_channel_endpoint_not_found():
    from httpx import ASGITransport, AsyncClient

    app = _make_app()
    from app.core.database import get_db
    app.dependency_overrides[get_db] = _make_db_override()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/sms/channels/ghost")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_channel_endpoint_not_found():
    from httpx import ASGITransport, AsyncClient

    app = _make_app()
    from app.core.database import get_db
    app.dependency_overrides[get_db] = _make_db_override()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete("/api/sms/channels/ghost")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_client_keys_endpoint_empty():
    from httpx import ASGITransport, AsyncClient

    app = _make_app()
    from app.core.database import get_db
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = []
    app.dependency_overrides[get_db] = _make_db_override(
        execute_side_effects=[count_result, rows_result]
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/sms/client-keys")
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_delete_client_key_endpoint_not_found():
    from httpx import ASGITransport, AsyncClient

    app = _make_app()
    from app.core.database import get_db
    app.dependency_overrides[get_db] = _make_db_override()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete("/api/sms/client-keys/ghost-key")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_policies_endpoint_empty():
    from httpx import ASGITransport, AsyncClient

    app = _make_app()
    from app.core.database import get_db
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = []
    app.dependency_overrides[get_db] = _make_db_override(
        execute_side_effects=[count_result, rows_result]
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/sms/policies")
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_get_policy_endpoint_not_found():
    from httpx import ASGITransport, AsyncClient

    app = _make_app()
    from app.core.database import get_db
    app.dependency_overrides[get_db] = _make_db_override()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/sms/policies/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_policy_endpoint_not_found():
    from httpx import ASGITransport, AsyncClient

    app = _make_app()
    from app.core.database import get_db
    app.dependency_overrides[get_db] = _make_db_override()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete("/api/sms/policies/nonexistent")
    assert resp.status_code == 404

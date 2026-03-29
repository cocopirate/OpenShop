"""Admin-side business logic: SMS template CRUD and configuration management."""
from typing import Optional

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.sms_config_store import SmsConfigStore
from app.models.sms_record import SmsRecord
from app.models.sms_template import SmsTemplate
from app.schemas.sms import SmsConfigUpdate, SmsTemplateCreate, SmsTemplateUpdate

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# SMS Template CRUD
# ---------------------------------------------------------------------------


async def list_templates(
    db: AsyncSession,
    provider: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[SmsTemplate], int]:
    """List SMS templates with optional filtering and pagination."""
    filters = []
    if provider:
        filters.append(SmsTemplate.provider == provider)
    if is_active is not None:
        filters.append(SmsTemplate.is_active == is_active)

    where_clause = and_(*filters) if filters else True

    total_result = await db.execute(
        select(func.count()).select_from(SmsTemplate).where(where_clause)
    )
    total = total_result.scalar_one()

    offset = (page - 1) * size
    rows = await db.execute(
        select(SmsTemplate)
        .where(where_clause)
        .order_by(SmsTemplate.id.asc())
        .offset(offset)
        .limit(size)
    )
    return list(rows.scalars().all()), total


async def get_template(db: AsyncSession, template_id: int) -> Optional[SmsTemplate]:
    """Fetch a single SMS template by primary key."""
    result = await db.execute(select(SmsTemplate).where(SmsTemplate.id == template_id))
    return result.scalar_one_or_none()


async def create_template(db: AsyncSession, data: SmsTemplateCreate) -> SmsTemplate:
    """Create a new SMS template."""
    template = SmsTemplate(
        provider_template_id=data.provider_template_id,
        name=data.name,
        content=data.content,
        provider=data.provider,
        is_active=data.is_active,
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    log.info("admin.template.created", template_id=template.id, name=template.name)
    return template


async def update_template(
    db: AsyncSession, template_id: int, data: SmsTemplateUpdate
) -> Optional[SmsTemplate]:
    """Update an existing SMS template. Returns None when not found."""
    template = await get_template(db, template_id)
    if template is None:
        return None

    changed = data.model_dump(exclude_unset=True)
    for field, value in changed.items():
        setattr(template, field, value)

    await db.flush()
    await db.refresh(template)
    log.info("admin.template.updated", template_id=template.id, changed=list(changed.keys()))
    return template


async def delete_template(db: AsyncSession, template_id: int) -> bool:
    """Delete an SMS template. Returns True when deleted, False when not found."""
    template = await get_template(db, template_id)
    if template is None:
        return False
    await db.delete(template)
    await db.flush()
    log.info("admin.template.deleted", template_id=template_id)
    return True


# ---------------------------------------------------------------------------
# SMS Record admin operations
# ---------------------------------------------------------------------------


async def delete_record(db: AsyncSession, record_id: int) -> bool:
    """Delete an SMS send record by ID. Returns True when deleted."""
    result = await db.execute(select(SmsRecord).where(SmsRecord.id == record_id))
    record = result.scalar_one_or_none()
    if record is None:
        return False
    await db.delete(record)
    await db.flush()
    log.info("admin.record.deleted", record_id=record_id)
    return True


# ---------------------------------------------------------------------------
# SMS Configuration management
# ---------------------------------------------------------------------------

# Keys to serialize into the persistent config store.
_PERSIST_KEYS = (
    "SMS_PROVIDER", "SMS_PROVIDER_FALLBACK", "SMS_PROVIDER_FAILURE_THRESHOLD",
    "SMS_PROVIDER_RECOVERY_TIMEOUT", "SMS_CODE_TTL",
    "SMS_RATE_LIMIT_PHONE_PER_MINUTE", "SMS_RATE_LIMIT_PHONE_PER_DAY",
    "SMS_RATE_LIMIT_IP_PER_MINUTE", "SMS_RATE_LIMIT_IP_PER_DAY",
    "SMS_RECORDS_RETENTION_DAYS", "SMS_CHANNELS", "SMS_CLIENT_KEYS",
    "CHUANGLAN_ACCOUNT", "CHUANGLAN_PASSWORD", "CHUANGLAN_API_URL",
    "ALIYUN_ACCESS_KEY_ID", "ALIYUN_ACCESS_KEY_SECRET",
    "ALIYUN_SMS_SIGN_NAME", "ALIYUN_SMS_ENDPOINT",
    "ALIYUN_PHONE_SVC_ACCESS_KEY_ID", "ALIYUN_PHONE_SVC_ACCESS_KEY_SECRET",
    "ALIYUN_PHONE_SVC_SIGN_NAME", "ALIYUN_PHONE_SVC_ENDPOINT",
    "TENCENT_SECRET_ID", "TENCENT_SECRET_KEY",
    "TENCENT_SMS_APP_ID", "TENCENT_SMS_SIGN_NAME",
)


def get_sms_config() -> dict:
    """Return a snapshot of the current runtime SMS configuration."""
    # Mask access_key_secret in channel configs
    masked_channels = {}
    for name, cfg in settings.SMS_CHANNELS.items():
        entry = dict(cfg)
        if entry.get("access_key_secret"):
            entry["access_key_secret"] = "***"
        masked_channels[name] = entry

    return {
        "sms_provider": settings.SMS_PROVIDER,
        "sms_provider_fallback": settings.SMS_PROVIDER_FALLBACK,
        "sms_provider_failure_threshold": settings.SMS_PROVIDER_FAILURE_THRESHOLD,
        "sms_provider_recovery_timeout": settings.SMS_PROVIDER_RECOVERY_TIMEOUT,
        "sms_code_ttl": settings.SMS_CODE_TTL,
        "sms_rate_limit_phone_per_minute": settings.SMS_RATE_LIMIT_PHONE_PER_MINUTE,
        "sms_rate_limit_phone_per_day": settings.SMS_RATE_LIMIT_PHONE_PER_DAY,
        "sms_rate_limit_ip_per_minute": settings.SMS_RATE_LIMIT_IP_PER_MINUTE,
        "sms_rate_limit_ip_per_day": settings.SMS_RATE_LIMIT_IP_PER_DAY,
        "sms_records_retention_days": settings.SMS_RECORDS_RETENTION_DAYS,
        "sms_channels": masked_channels,
        "sms_client_keys": dict(settings.SMS_CLIENT_KEYS),
        # Provider credentials – secrets masked
        "chuanglan": {
            "account": settings.CHUANGLAN_ACCOUNT,
            "password": "***" if settings.CHUANGLAN_PASSWORD else "",
            "api_url": settings.CHUANGLAN_API_URL,
        },
        "aliyun": {
            "access_key_id": settings.ALIYUN_ACCESS_KEY_ID,
            "access_key_secret": "***" if settings.ALIYUN_ACCESS_KEY_SECRET else "",
            "sign_name": settings.ALIYUN_SMS_SIGN_NAME,
            "endpoint": settings.ALIYUN_SMS_ENDPOINT,
        },
        "aliyun_phone_svc": {
            "access_key_id": settings.ALIYUN_PHONE_SVC_ACCESS_KEY_ID,
            "access_key_secret": "***" if settings.ALIYUN_PHONE_SVC_ACCESS_KEY_SECRET else "",
            "sign_name": settings.ALIYUN_PHONE_SVC_SIGN_NAME,
            "endpoint": settings.ALIYUN_PHONE_SVC_ENDPOINT,
        },
        "tencent": {
            "secret_id": settings.TENCENT_SECRET_ID,
            "secret_key": "***" if settings.TENCENT_SECRET_KEY else "",
            "app_id": settings.TENCENT_SMS_APP_ID,
            "sign_name": settings.TENCENT_SMS_SIGN_NAME,
        },
    }


async def _persist_config(db: AsyncSession) -> None:
    """Serialize current settings to the config store table (upsert id=1)."""
    config = {key: getattr(settings, key) for key in _PERSIST_KEYS}
    result = await db.execute(select(SmsConfigStore).where(SmsConfigStore.id == 1))
    store = result.scalar_one_or_none()
    if store:
        store.config_json = config
    else:
        db.add(SmsConfigStore(id=1, config_json=config))
    await db.flush()


async def load_persisted_config(db: AsyncSession) -> None:
    """Load stored config from DB and apply over the env-var defaults in settings."""
    result = await db.execute(select(SmsConfigStore).where(SmsConfigStore.id == 1))
    store = result.scalar_one_or_none()
    if not store:
        return
    for key, value in store.config_json.items():
        if hasattr(settings, key) and value is not None:
            setattr(settings, key, value)
    log.info("admin.config.loaded_from_db")


async def update_sms_config(data: SmsConfigUpdate, db: AsyncSession) -> dict:
    """Apply a partial update to the runtime SMS configuration and persist to DB.

    Changes take effect immediately in-process and are written to the
    ``sms_config_store`` table so they survive service restarts.
    """
    changed = data.model_dump(exclude_unset=True)
    scalar_mapping = {
        "sms_provider": "SMS_PROVIDER",
        "sms_provider_fallback": "SMS_PROVIDER_FALLBACK",
        "sms_provider_failure_threshold": "SMS_PROVIDER_FAILURE_THRESHOLD",
        "sms_provider_recovery_timeout": "SMS_PROVIDER_RECOVERY_TIMEOUT",
        "sms_code_ttl": "SMS_CODE_TTL",
        "sms_rate_limit_phone_per_minute": "SMS_RATE_LIMIT_PHONE_PER_MINUTE",
        "sms_rate_limit_phone_per_day": "SMS_RATE_LIMIT_PHONE_PER_DAY",
        "sms_rate_limit_ip_per_minute": "SMS_RATE_LIMIT_IP_PER_MINUTE",
        "sms_rate_limit_ip_per_day": "SMS_RATE_LIMIT_IP_PER_DAY",
        "sms_records_retention_days": "SMS_RECORDS_RETENTION_DAYS",
    }
    for field, value in changed.items():
        if field in scalar_mapping:
            setattr(settings, scalar_mapping[field], value)

    # Merge sms_channels: null value = delete channel entry
    if data.sms_channels is not None:
        channels = dict(settings.SMS_CHANNELS)
        for name, cfg in data.sms_channels.items():
            if cfg is None:
                channels.pop(name, None)
            else:
                channels[name] = cfg.model_dump(exclude_none=True)
        settings.SMS_CHANNELS = channels

    # Merge sms_client_keys: null value = delete key entry
    if data.sms_client_keys is not None:
        keys = dict(settings.SMS_CLIENT_KEYS)
        for api_key, channel in data.sms_client_keys.items():
            if channel is None:
                keys.pop(api_key, None)
            else:
                keys[api_key] = channel
        settings.SMS_CLIENT_KEYS = keys

    # Provider credentials – apply only the supplied (non-None) fields
    if data.chuanglan:
        creds = data.chuanglan.model_dump(exclude_none=True)
        _chuanglan_map = {
            "account": "CHUANGLAN_ACCOUNT",
            "password": "CHUANGLAN_PASSWORD",
            "api_url": "CHUANGLAN_API_URL",
        }
        for field, key in _chuanglan_map.items():
            if field in creds:
                setattr(settings, key, creds[field])

    if data.aliyun:
        creds = data.aliyun.model_dump(exclude_none=True)
        _aliyun_map = {
            "access_key_id": "ALIYUN_ACCESS_KEY_ID",
            "access_key_secret": "ALIYUN_ACCESS_KEY_SECRET",
            "sign_name": "ALIYUN_SMS_SIGN_NAME",
            "endpoint": "ALIYUN_SMS_ENDPOINT",
        }
        for field, key in _aliyun_map.items():
            if field in creds:
                setattr(settings, key, creds[field])

    if data.aliyun_phone_svc:
        creds = data.aliyun_phone_svc.model_dump(exclude_none=True)
        _pns_map = {
            "access_key_id": "ALIYUN_PHONE_SVC_ACCESS_KEY_ID",
            "access_key_secret": "ALIYUN_PHONE_SVC_ACCESS_KEY_SECRET",
            "sign_name": "ALIYUN_PHONE_SVC_SIGN_NAME",
            "endpoint": "ALIYUN_PHONE_SVC_ENDPOINT",
        }
        for field, key in _pns_map.items():
            if field in creds:
                setattr(settings, key, creds[field])

    if data.tencent:
        creds = data.tencent.model_dump(exclude_none=True)
        _tencent_map = {
            "secret_id": "TENCENT_SECRET_ID",
            "secret_key": "TENCENT_SECRET_KEY",
            "app_id": "TENCENT_SMS_APP_ID",
            "sign_name": "TENCENT_SMS_SIGN_NAME",
        }
        for field, key in _tencent_map.items():
            if field in creds:
                setattr(settings, key, creds[field])

    await _persist_config(db)
    await db.commit()
    log.info("admin.config.updated", changed=list(changed.keys()))
    return get_sms_config()

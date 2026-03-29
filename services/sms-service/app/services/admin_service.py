"""Admin-side business logic: SMS template CRUD and configuration management."""
from typing import Optional

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.sms_config_store import SmsConfigStore
from app.models.sms_record import SmsRecord
from app.models.sms_template import SmsTemplate
from app.schemas.sms import (
    SmsChannelCreate,
    SmsChannelOut,
    SmsChannelUpdate,
    SmsClientKeyCreate,
    SmsClientKeyOut,
    SmsConfigUpdate,
    SmsTemplateCreate,
    SmsTemplateUpdate,
)

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

_PERSIST_KEYS = (
    "SMS_DEFAULT_CHANNEL",
    "SMS_CODE_TTL",
    "SMS_RATE_LIMIT_PHONE_PER_MINUTE", "SMS_RATE_LIMIT_PHONE_PER_DAY",
    "SMS_RATE_LIMIT_IP_PER_MINUTE", "SMS_RATE_LIMIT_IP_PER_DAY",
    "SMS_RECORDS_RETENTION_DAYS",
    "SMS_CHANNELS", "SMS_CLIENT_KEYS",
)


def get_sms_config() -> dict:
    """Return a snapshot of the current runtime SMS configuration."""
    masked_channels = {}
    for name, cfg in settings.SMS_CHANNELS.items():
        masked_channels[name] = _mask_channel_dict(cfg)

    return {
        "sms_default_channel": settings.SMS_DEFAULT_CHANNEL,
        "sms_code_ttl": settings.SMS_CODE_TTL,
        "sms_rate_limit_phone_per_minute": settings.SMS_RATE_LIMIT_PHONE_PER_MINUTE,
        "sms_rate_limit_phone_per_day": settings.SMS_RATE_LIMIT_PHONE_PER_DAY,
        "sms_rate_limit_ip_per_minute": settings.SMS_RATE_LIMIT_IP_PER_MINUTE,
        "sms_rate_limit_ip_per_day": settings.SMS_RATE_LIMIT_IP_PER_DAY,
        "sms_records_retention_days": settings.SMS_RECORDS_RETENTION_DAYS,
        "sms_channels": masked_channels,
        "sms_client_keys": dict(settings.SMS_CLIENT_KEYS),
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
    """Load stored config from DB and apply over the defaults in settings."""
    result = await db.execute(select(SmsConfigStore).where(SmsConfigStore.id == 1))
    store = result.scalar_one_or_none()
    if not store:
        return
    for key, value in store.config_json.items():
        if hasattr(settings, key) and value is not None:
            setattr(settings, key, value)
    log.info("admin.config.loaded_from_db")


async def update_sms_config(data: SmsConfigUpdate, db: AsyncSession) -> dict:
    """Apply a partial update to the runtime SMS configuration and persist to DB."""
    scalar_mapping = {
        "sms_default_channel": "SMS_DEFAULT_CHANNEL",
        "sms_code_ttl": "SMS_CODE_TTL",
        "sms_rate_limit_phone_per_minute": "SMS_RATE_LIMIT_PHONE_PER_MINUTE",
        "sms_rate_limit_phone_per_day": "SMS_RATE_LIMIT_PHONE_PER_DAY",
        "sms_rate_limit_ip_per_minute": "SMS_RATE_LIMIT_IP_PER_MINUTE",
        "sms_rate_limit_ip_per_day": "SMS_RATE_LIMIT_IP_PER_DAY",
        "sms_records_retention_days": "SMS_RECORDS_RETENTION_DAYS",
    }
    changed = data.model_dump(exclude_unset=True)
    for field, value in changed.items():
        if field in scalar_mapping:
            setattr(settings, scalar_mapping[field], value)

    await _persist_config(db)
    await db.commit()
    log.info("admin.config.updated", changed=list(changed.keys()))
    return get_sms_config()


# ---------------------------------------------------------------------------
# SMS Channel CRUD
# ---------------------------------------------------------------------------

_SECRET_FIELDS = {"access_key_secret", "password", "secret_key"}


def _mask_channel_dict(cfg: dict) -> dict:
    return {k: ("***" if k in _SECRET_FIELDS and v else v) for k, v in cfg.items()}


def _mask_channel(name: str, cfg: dict) -> SmsChannelOut:
    """Return a SmsChannelOut with secret fields masked."""
    masked = _mask_channel_dict(cfg)
    return SmsChannelOut(name=name, **masked)


def list_channels() -> tuple[list[SmsChannelOut], int]:
    """Return all configured channels with secrets masked."""
    items = [_mask_channel(n, c) for n, c in settings.SMS_CHANNELS.items()]
    return items, len(items)


def get_channel(name: str) -> SmsChannelOut | None:
    """Return a single channel by name, or None if not found."""
    cfg = settings.SMS_CHANNELS.get(name)
    if cfg is None:
        return None
    return _mask_channel(name, cfg)


async def upsert_channel(name: str, data: SmsChannelCreate, db: AsyncSession) -> SmsChannelOut:
    """Create or fully replace a named channel and persist."""
    channels = dict(settings.SMS_CHANNELS)
    channels[name] = data.model_dump(exclude_none=True)
    settings.SMS_CHANNELS = channels
    await _persist_config(db)
    await db.commit()
    log.info("admin.channel.upserted", channel=name)
    return _mask_channel(name, channels[name])


async def patch_channel(name: str, data: SmsChannelUpdate, db: AsyncSession) -> SmsChannelOut | None:
    """Partially update a named channel. Returns None if not found."""
    channels = dict(settings.SMS_CHANNELS)
    if name not in channels:
        return None
    existing = dict(channels[name])
    for key, value in data.model_dump(exclude_unset=True).items():
        existing[key] = value
    channels[name] = existing
    settings.SMS_CHANNELS = channels
    await _persist_config(db)
    await db.commit()
    log.info("admin.channel.patched", channel=name)
    return _mask_channel(name, existing)


async def delete_channel(name: str, db: AsyncSession) -> bool:
    """Delete a named channel. Returns True when deleted, False when not found."""
    channels = dict(settings.SMS_CHANNELS)
    if name not in channels:
        return False
    del channels[name]
    settings.SMS_CHANNELS = channels
    await _persist_config(db)
    await db.commit()
    log.info("admin.channel.deleted", channel=name)
    return True


# ---------------------------------------------------------------------------
# SMS Client Key CRUD
# ---------------------------------------------------------------------------


def list_client_keys() -> tuple[list[SmsClientKeyOut], int]:
    """Return all configured client-key→channel mappings."""
    items = [SmsClientKeyOut(api_key=k, channel=v) for k, v in settings.SMS_CLIENT_KEYS.items()]
    return items, len(items)


async def create_client_key(data: SmsClientKeyCreate, db: AsyncSession) -> SmsClientKeyOut:
    """Add (or overwrite) a client-key mapping and persist."""
    keys = dict(settings.SMS_CLIENT_KEYS)
    keys[data.api_key] = data.channel
    settings.SMS_CLIENT_KEYS = keys
    await _persist_config(db)
    await db.commit()
    log.info("admin.client_key.created", api_key=data.api_key[:4] + "****", channel=data.channel)
    return SmsClientKeyOut(api_key=data.api_key, channel=data.channel)


async def delete_client_key(api_key: str, db: AsyncSession) -> bool:
    """Delete a client-key mapping. Returns True when deleted, False when not found."""
    keys = dict(settings.SMS_CLIENT_KEYS)
    if api_key not in keys:
        return False
    del keys[api_key]
    settings.SMS_CLIENT_KEYS = keys
    await _persist_config(db)
    await db.commit()
    log.info("admin.client_key.deleted", api_key=api_key[:4] + "****")
    return True

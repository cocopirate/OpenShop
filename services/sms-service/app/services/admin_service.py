"""Admin-side business logic: SMS template CRUD and configuration management."""
from typing import Optional

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
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


def get_sms_config() -> dict:
    """Return a snapshot of the current runtime SMS configuration."""
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
    }


def update_sms_config(data: SmsConfigUpdate) -> dict:
    """Apply a partial update to the runtime SMS configuration.

    NOTE: Changes take effect immediately in-process but are **not** persisted to
    `.env` or a database. To make changes permanent, update the environment
    variables and restart the service.
    """
    changed = data.model_dump(exclude_unset=True)
    mapping = {
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
        attr = mapping[field]
        setattr(settings, attr, value)

    log.info("admin.config.updated", changed=list(changed.keys()))
    return get_sms_config()

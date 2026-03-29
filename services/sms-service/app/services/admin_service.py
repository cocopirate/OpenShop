"""Admin-side business logic: SMS template, policy, channel and client-key CRUD."""
from typing import Optional

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sms_channel import SmsChannel
from app.models.sms_client_key import SmsClientKey
from app.models.sms_policy import SmsPolicy
from app.models.sms_record import SmsRecord
from app.models.sms_template import SmsTemplate
from app.schemas.sms import (
    SmsChannelCreate,
    SmsChannelOut,
    SmsChannelUpdate,
    SmsClientKeyCreate,
    SmsClientKeyOut,
    SmsPolicyCreate,
    SmsPolicyOut,
    SmsPolicyUpdate,
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
# SMS Policy CRUD
# ---------------------------------------------------------------------------


async def list_policies(db: AsyncSession) -> tuple[list[SmsPolicy], int]:
    """Return all policies."""
    total_result = await db.execute(select(func.count()).select_from(SmsPolicy))
    total = total_result.scalar_one()
    rows = await db.execute(select(SmsPolicy).order_by(SmsPolicy.name.asc()))
    return list(rows.scalars().all()), total


async def get_policy(db: AsyncSession, name: str) -> Optional[SmsPolicy]:
    """Fetch a single policy by name."""
    result = await db.execute(select(SmsPolicy).where(SmsPolicy.name == name))
    return result.scalar_one_or_none()


async def upsert_policy(db: AsyncSession, name: str, data: SmsPolicyCreate) -> SmsPolicy:
    """Create or fully replace a named policy."""
    existing = await get_policy(db, name)
    if existing:
        for field, value in data.model_dump().items():
            setattr(existing, field, value)
        await db.flush()
        await db.refresh(existing)
        log.info("admin.policy.replaced", policy=name)
        return existing

    policy = SmsPolicy(name=name, **data.model_dump())
    db.add(policy)
    await db.flush()
    await db.refresh(policy)
    log.info("admin.policy.created", policy=name)
    return policy


async def patch_policy(
    db: AsyncSession, name: str, data: SmsPolicyUpdate
) -> Optional[SmsPolicy]:
    """Partially update a named policy. Returns None if not found."""
    policy = await get_policy(db, name)
    if policy is None:
        return None

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(policy, field, value)

    await db.flush()
    await db.refresh(policy)
    log.info("admin.policy.patched", policy=name)
    return policy


async def delete_policy(db: AsyncSession, name: str) -> tuple[bool, bool]:
    """Delete a named policy.

    Returns (deleted, in_use):
      - (True, False)  – deleted successfully
      - (False, False) – not found
      - (False, True)  – policy is referenced by at least one channel
    """
    policy = await get_policy(db, name)
    if policy is None:
        return False, False

    # Check if any channel references this policy
    ref_result = await db.execute(
        select(func.count()).select_from(SmsChannel).where(SmsChannel.policy_name == name)
    )
    if ref_result.scalar_one() > 0:
        return False, True

    await db.delete(policy)
    await db.flush()
    log.info("admin.policy.deleted", policy=name)
    return True, False


# ---------------------------------------------------------------------------
# SMS Channel CRUD
# ---------------------------------------------------------------------------

_SECRET_FIELDS = {"access_key_secret", "password", "secret_key"}


def _mask_channel(channel: SmsChannel) -> SmsChannelOut:
    """Return a SmsChannelOut with secret fields masked."""
    out = SmsChannelOut.model_validate(channel)
    if out.access_key_secret:
        out.access_key_secret = "***"
    if out.password:
        out.password = "***"
    if out.secret_key:
        out.secret_key = "***"
    return out


async def list_channels(db: AsyncSession) -> tuple[list[SmsChannelOut], int]:
    """Return all configured channels with secrets masked."""
    total_result = await db.execute(select(func.count()).select_from(SmsChannel))
    total = total_result.scalar_one()
    rows = await db.execute(select(SmsChannel).order_by(SmsChannel.name.asc()))
    items = [_mask_channel(ch) for ch in rows.scalars().all()]
    return items, total


async def get_channel(db: AsyncSession, name: str) -> Optional[SmsChannelOut]:
    """Return a single channel by name (masked), or None if not found."""
    result = await db.execute(select(SmsChannel).where(SmsChannel.name == name))
    channel = result.scalar_one_or_none()
    if channel is None:
        return None
    return _mask_channel(channel)


async def get_channel_raw(db: AsyncSession, name: str) -> Optional[SmsChannel]:
    """Return the raw (unmasked) SmsChannel ORM object, or None."""
    result = await db.execute(select(SmsChannel).where(SmsChannel.name == name))
    return result.scalar_one_or_none()


async def get_default_channel(db: AsyncSession) -> Optional[SmsChannel]:
    """Return the channel marked as default, or the first channel if none marked."""
    result = await db.execute(
        select(SmsChannel).where(SmsChannel.is_default.is_(True)).limit(1)
    )
    channel = result.scalar_one_or_none()
    if channel is None:
        # Fallback: first channel by name
        result = await db.execute(select(SmsChannel).order_by(SmsChannel.name.asc()).limit(1))
        channel = result.scalar_one_or_none()
    return channel


async def upsert_channel(
    db: AsyncSession, name: str, data: SmsChannelCreate
) -> SmsChannelOut:
    """Create or fully replace a named channel."""
    existing = await get_channel_raw(db, name)

    if data.is_default:
        # Clear is_default from any other channel
        rows = await db.execute(
            select(SmsChannel).where(SmsChannel.is_default.is_(True), SmsChannel.name != name)
        )
        for ch in rows.scalars().all():
            ch.is_default = False

    if existing:
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(existing, field, value)
        # Explicitly clear fields not provided (full replace)
        for field in data.model_fields:
            if data.model_dump().get(field) is None:
                setattr(existing, field, None)
        # provider and is_default always set
        existing.provider = data.provider
        existing.is_default = data.is_default
        await db.flush()
        await db.refresh(existing)
        log.info("admin.channel.replaced", channel=name)
        return _mask_channel(existing)

    channel = SmsChannel(name=name, **data.model_dump())
    db.add(channel)
    await db.flush()
    await db.refresh(channel)
    log.info("admin.channel.created", channel=name)
    return _mask_channel(channel)


async def patch_channel(
    db: AsyncSession, name: str, data: SmsChannelUpdate
) -> Optional[SmsChannelOut]:
    """Partially update a named channel. Returns None if not found."""
    channel = await get_channel_raw(db, name)
    if channel is None:
        return None

    changed = data.model_dump(exclude_unset=True)

    if changed.get("is_default"):
        # Clear is_default from any other channel
        rows = await db.execute(
            select(SmsChannel).where(SmsChannel.is_default.is_(True), SmsChannel.name != name)
        )
        for ch in rows.scalars().all():
            ch.is_default = False

    for field, value in changed.items():
        setattr(channel, field, value)

    await db.flush()
    await db.refresh(channel)
    log.info("admin.channel.patched", channel=name)
    return _mask_channel(channel)


async def delete_channel(db: AsyncSession, name: str) -> bool:
    """Delete a named channel. Returns True when deleted, False when not found."""
    channel = await get_channel_raw(db, name)
    if channel is None:
        return False
    await db.delete(channel)
    await db.flush()
    log.info("admin.channel.deleted", channel=name)
    return True


# ---------------------------------------------------------------------------
# SMS Client Key CRUD
# ---------------------------------------------------------------------------


async def list_client_keys(db: AsyncSession) -> tuple[list[SmsClientKeyOut], int]:
    """Return all configured client-key→channel mappings."""
    total_result = await db.execute(select(func.count()).select_from(SmsClientKey))
    total = total_result.scalar_one()
    rows = await db.execute(select(SmsClientKey).order_by(SmsClientKey.api_key.asc()))
    items = [SmsClientKeyOut(api_key=k.api_key, channel=k.channel) for k in rows.scalars().all()]
    return items, total


async def get_client_key_channel(db: AsyncSession, api_key: str) -> Optional[str]:
    """Return the channel name for an API key, or None if not found."""
    result = await db.execute(
        select(SmsClientKey.channel).where(SmsClientKey.api_key == api_key)
    )
    return result.scalar_one_or_none()


async def create_client_key(db: AsyncSession, data: SmsClientKeyCreate) -> SmsClientKeyOut:
    """Add or overwrite a client-key mapping."""
    result = await db.execute(
        select(SmsClientKey).where(SmsClientKey.api_key == data.api_key)
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.channel = data.channel
    else:
        db.add(SmsClientKey(api_key=data.api_key, channel=data.channel))
    await db.flush()
    log.info("admin.client_key.created", api_key=data.api_key[:4] + "****", channel=data.channel)
    return SmsClientKeyOut(api_key=data.api_key, channel=data.channel)


async def delete_client_key(db: AsyncSession, api_key: str) -> bool:
    """Delete a client-key mapping. Returns True when deleted, False when not found."""
    result = await db.execute(select(SmsClientKey).where(SmsClientKey.api_key == api_key))
    key = result.scalar_one_or_none()
    if key is None:
        return False
    await db.delete(key)
    await db.flush()
    log.info("admin.client_key.deleted", api_key=api_key[:4] + "****")
    return True

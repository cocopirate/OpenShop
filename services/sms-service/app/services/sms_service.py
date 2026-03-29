"""SMS business logic service."""
import secrets
import time
from typing import Optional

import structlog
from sqlalchemy import and_, delete, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.masking import mask_phone
from app.core.metrics import sms_send_latency, sms_send_total
from app.core.redis import get_redis
from app.models.sms_channel import SmsChannel
from app.models.sms_policy import SmsPolicy
from app.models.sms_record import SmsRecord, SmsStatus
from app.providers import SendResult
from app.providers.factory import get_provider, record_provider_failure, record_provider_success

log = structlog.get_logger(__name__)

_DIGITS = "0123456789"
_IDEMPOTENCY_TTL = 86400  # 24 hours

# Default policy values (used when no policy found in DB)
_DEFAULT_CODE_TTL = 300
_DEFAULT_FAILURE_THRESHOLD = 3
_DEFAULT_RECOVERY_TIMEOUT = 60


def _make_verify_key(phone: str) -> str:
    return f"sms:verify:{phone}"


def _make_idempotency_key(request_id: str) -> str:
    return f"sms:idempotency:{request_id}"


def _channel_to_credentials(channel: SmsChannel) -> dict:
    """Convert SmsChannel ORM object to credentials dict for the provider factory."""
    return {
        "provider": channel.provider,
        "access_key_id": channel.access_key_id,
        "access_key_secret": channel.access_key_secret,
        "sign_name": channel.sign_name,
        "endpoint": channel.endpoint,
        "account": channel.account,
        "password": channel.password,
        "api_url": channel.api_url,
        "app_id": channel.app_id,
        "secret_id": channel.secret_id,
        "secret_key": channel.secret_key,
    }


async def _resolve_channel_and_policy(
    db: AsyncSession,
    channel_name: Optional[str],
) -> tuple[SmsChannel, SmsPolicy]:
    """Return the (channel, policy) pair for the given channel name.

    If ``channel_name`` is None, the default channel is used.
    If no policy is associated, the ``default`` policy is used.
    Falls back to in-memory defaults if neither exists in DB.
    """
    from app.services.admin_service import get_default_channel, get_channel_raw

    if channel_name:
        channel = await get_channel_raw(db, channel_name)
    else:
        channel = await get_default_channel(db)

    # Synthesise a minimal in-memory channel when DB has none configured yet
    if channel is None:
        channel = SmsChannel(
            name=channel_name or "_default",
            provider="aliyun",
            is_default=True,
        )

    # Resolve policy
    policy_name = channel.policy_name or "default"
    result = await db.execute(select(SmsPolicy).where(SmsPolicy.name == policy_name))
    policy = result.scalar_one_or_none()

    if policy is None:
        # Fall back to in-memory defaults
        policy = SmsPolicy(
            name=policy_name,
            code_ttl=_DEFAULT_CODE_TTL,
            failure_threshold=_DEFAULT_FAILURE_THRESHOLD,
            recovery_timeout=_DEFAULT_RECOVERY_TIMEOUT,
            rate_limit_phone_per_minute=1,
            rate_limit_phone_per_day=10,
            rate_limit_ip_per_minute=10,
            rate_limit_ip_per_day=100,
            records_retention_days=90,
        )

    return channel, policy


async def send_sms(
    db: AsyncSession,
    phone: str,
    template_id: str,
    params: dict,
    request_id: Optional[str] = None,
    channel_name: Optional[str] = None,
) -> SmsRecord:
    """Send an SMS and persist a send record. Handles idempotency."""
    redis = get_redis()
    phone_masked = mask_phone(phone)
    idem_key: Optional[str] = None

    # Idempotency check
    if request_id:
        idem_key = _make_idempotency_key(request_id)
        cached_id = await redis.get(idem_key)
        if cached_id:
            log.info("sms.send.duplicate", request_id=request_id, phone_masked=phone_masked)
            result = await db.execute(
                select(SmsRecord).where(SmsRecord.id == int(cached_id))
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing

    channel, policy = await _resolve_channel_and_policy(db, channel_name)
    effective_channel = channel.name

    # Resolve fallback credentials if policy specifies a fallback channel
    fallback_creds: Optional[dict] = None
    if policy.fallback_channel:
        from app.services.admin_service import get_channel_raw as _get_raw
        fallback_ch = await _get_raw(db, policy.fallback_channel)
        if fallback_ch:
            fallback_creds = _channel_to_credentials(fallback_ch)

    provider = get_provider(
        channel_name=effective_channel,
        channel_credentials=_channel_to_credentials(channel),
        failure_threshold=policy.failure_threshold,
        recovery_timeout=policy.recovery_timeout,
        fallback_channel_name=policy.fallback_channel,
        fallback_credentials=fallback_creds,
    )

    log.info(
        "sms.send.start",
        phone_masked=phone_masked,
        template_id=template_id,
        provider=channel.provider,
        channel=effective_channel,
        request_id=request_id,
    )

    start_time = time.monotonic()
    send_result: SendResult = await provider.send(phone, template_id, params)
    elapsed = time.monotonic() - start_time

    status_label = "success" if send_result.success else "failed"
    sms_send_total.labels(provider=channel.provider, status=status_label).inc()
    sms_send_latency.labels(provider=channel.provider).observe(elapsed)

    if send_result.success:
        record_provider_success(effective_channel)
        log.info(
            "sms.send.success",
            phone_masked=phone_masked,
            provider=channel.provider,
            provider_message_id=send_result.provider_message_id,
            latency_ms=round(elapsed * 1000, 2),
        )
        if send_result.verification_code:
            vc_key = _make_verify_key(phone)
            await redis.set(vc_key, send_result.verification_code, ex=policy.code_ttl)
    else:
        record_provider_failure(effective_channel, failure_threshold=policy.failure_threshold)
        log.error(
            "sms.send.failed",
            phone_masked=phone_masked,
            provider=channel.provider,
            error_code=send_result.error_code,
            error_message=send_result.error_message,
        )

    record = SmsRecord(
        request_id=request_id,
        phone=phone,
        phone_masked=phone_masked,
        template_id=template_id,
        provider=channel.provider,
        provider_message_id=send_result.provider_message_id or None,
        status=SmsStatus.SENT if send_result.success else SmsStatus.FAILED,
        error_code=send_result.error_code or None,
        error_message=send_result.error_message or None,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)

    if request_id and idem_key:
        await redis.set(idem_key, str(record.id), ex=_IDEMPOTENCY_TTL)

    if not send_result.success:
        raise RuntimeError(
            send_result.error_message or send_result.error_code or "SMS provider send failed"
        )

    return record


async def send_verification_code(
    db: AsyncSession,
    phone: str,
    template_id: str,
    channel_name: Optional[str] = None,
) -> SmsRecord:
    """Generate and send a verification code.

    A local 6-digit OTP is generated and cached in Redis for all providers.
    The code and its validity period (minutes) are passed as template params
    so the SMS content can render them correctly.
    """
    code = "".join(secrets.choice(_DIGITS) for _ in range(6))
    redis = get_redis()
    key = _make_verify_key(phone)

    _, policy = await _resolve_channel_and_policy(db, channel_name)
    await redis.set(key, code, ex=policy.code_ttl)
    min_str = str(max(1, policy.code_ttl // 60))
    return await send_sms(db, phone, template_id, {"code": code, "min": min_str}, channel_name=channel_name)


async def verify_code(phone: str, code: str) -> bool:
    """Check a verification code from Redis cache (all providers unified)."""
    redis = get_redis()
    key = _make_verify_key(phone)
    stored = await redis.get(key)
    if stored and stored == code:
        await redis.delete(key)
        return True
    return False


async def get_sms_records(
    db: AsyncSession,
    phone: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    status: Optional[SmsStatus] = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[SmsRecord], int]:
    """Query SMS records with filtering and pagination. Returns (records, total)."""
    from datetime import datetime

    filters = []
    if phone:
        filters.append(SmsRecord.phone == phone)
    if start_time:
        filters.append(SmsRecord.created_at >= datetime.fromisoformat(start_time))
    if end_time:
        filters.append(SmsRecord.created_at <= datetime.fromisoformat(end_time))
    if status:
        filters.append(SmsRecord.status == status)

    where_clause = and_(*filters) if filters else true()

    total_result = await db.execute(
        select(func.count()).select_from(SmsRecord).where(where_clause)
    )
    total = total_result.scalar_one()

    offset = (page - 1) * size
    records_result = await db.execute(
        select(SmsRecord)
        .where(where_clause)
        .order_by(SmsRecord.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    return list(records_result.scalars().all()), total


async def cleanup_old_records(db: AsyncSession) -> int:
    """Delete SMS records older than the default policy's records_retention_days.

    Returns count deleted. If retention_days is 0, no records are deleted.
    """
    result = await db.execute(select(SmsPolicy).where(SmsPolicy.name == "default"))
    policy = result.scalar_one_or_none()
    retention_days = policy.records_retention_days if policy else 90

    if not retention_days:
        return 0
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    result = await db.execute(
        delete(SmsRecord).where(SmsRecord.created_at < cutoff)
    )
    count = result.rowcount
    if count:
        log.info("sms.records.cleanup", deleted_count=count, cutoff=cutoff.isoformat())
    return count


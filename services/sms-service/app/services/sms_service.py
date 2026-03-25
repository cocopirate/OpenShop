"""SMS business logic service."""
import secrets
import time
from typing import Optional

import structlog
from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.masking import mask_phone
from app.core.metrics import sms_send_latency, sms_send_total
from app.core.redis import get_redis
from app.models.sms_record import SmsRecord, SmsStatus
from app.providers import SendResult
from app.providers.factory import get_provider, record_provider_failure, record_provider_success

log = structlog.get_logger(__name__)

_DIGITS = "0123456789"
_IDEMPOTENCY_TTL = 86400  # 24 hours


def _make_verify_key(phone: str) -> str:
    return f"sms:verify:{phone}"


def _make_idempotency_key(request_id: str) -> str:
    return f"sms:idempotency:{request_id}"


async def send_sms(
    db: AsyncSession,
    phone: str,
    template_id: str,
    params: dict,
    request_id: Optional[str] = None,
) -> SmsRecord:
    """Send an SMS and persist a send record. Handles idempotency."""
    redis = get_redis()
    phone_masked = mask_phone(phone)

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

    provider = get_provider()
    provider_name = settings.SMS_PROVIDER

    log.info(
        "sms.send.start",
        phone_masked=phone_masked,
        template_id=template_id,
        provider=provider_name,
        request_id=request_id,
    )

    start_time = time.monotonic()
    send_result: SendResult = await provider.send(phone, template_id, params)
    elapsed = time.monotonic() - start_time

    status_label = "success" if send_result.success else "failed"
    sms_send_total.labels(provider=provider_name, status=status_label).inc()
    sms_send_latency.labels(provider=provider_name).observe(elapsed)

    if send_result.success:
        record_provider_success()
        log.info(
            "sms.send.success",
            phone_masked=phone_masked,
            provider=provider_name,
            provider_message_id=send_result.provider_message_id,
            latency_ms=round(elapsed * 1000, 2),
        )
    else:
        record_provider_failure()
        log.error(
            "sms.send.failed",
            phone_masked=phone_masked,
            provider=provider_name,
            error_code=send_result.error_code,
            error_message=send_result.error_message,
        )

    record = SmsRecord(
        request_id=request_id,
        phone=phone,
        phone_masked=phone_masked,
        template_id=template_id,
        provider=provider_name,
        provider_message_id=send_result.provider_message_id or None,
        status=SmsStatus.SENT if send_result.success else SmsStatus.FAILED,
        error_code=send_result.error_code or None,
        error_message=send_result.error_message or None,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)

    if request_id:
        await redis.set(idem_key, str(record.id), ex=_IDEMPOTENCY_TTL)

    return record


async def send_verification_code(
    db: AsyncSession,
    phone: str,
    template_id: str,
) -> str:
    """Generate a 6-digit OTP, cache in Redis, and send via SMS."""
    code = "".join(secrets.choice(_DIGITS) for _ in range(6))
    redis = get_redis()
    key = _make_verify_key(phone)
    await redis.set(key, code, ex=settings.SMS_CODE_TTL)
    await send_sms(db, phone, template_id, {"code": code})
    return code


async def verify_code(phone: str, code: str) -> bool:
    """Check a verification code from Redis cache."""
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

    where_clause = and_(*filters) if filters else True

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
    """Delete SMS records older than SMS_RECORDS_RETENTION_DAYS. Returns count deleted."""
    if not settings.SMS_RECORDS_RETENTION_DAYS:
        return 0
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.SMS_RECORDS_RETENTION_DAYS)
    result = await db.execute(
        delete(SmsRecord).where(SmsRecord.created_at < cutoff)
    )
    count = result.rowcount
    if count:
        log.info("sms.records.cleanup", deleted_count=count, cutoff=cutoff.isoformat())
    return count


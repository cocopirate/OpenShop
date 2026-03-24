"""SMS business logic service."""

import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import get_redis
from app.models.sms_record import SmsRecord, SmsStatus
from app.providers import BaseSmsProvider, SendResult
from app.providers.aliyun import AliyunSmsProvider
from app.providers.tencent import TencentSmsProvider


def get_provider() -> BaseSmsProvider:
    """Return the active SMS provider based on configuration."""
    if settings.SMS_PROVIDER == "tencent":
        return TencentSmsProvider()
    return AliyunSmsProvider()


def _make_verify_key(phone: str) -> str:
    return f"sms:verify:{phone}"


async def send_sms(
    db: AsyncSession,
    phone: str,
    template_id: str,
    params: dict,
) -> SmsRecord:
    """Send an SMS and persist a send record."""
    provider = get_provider()
    result: SendResult = await provider.send(phone, template_id, params)

    record = SmsRecord(
        phone=phone,
        template_id=template_id,
        provider=settings.SMS_PROVIDER,
        provider_message_id=result.provider_message_id or None,
        status=SmsStatus.SENT if result.success else SmsStatus.FAILED,
        error_message=result.error_message or None,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


async def send_verification_code(
    db: AsyncSession,
    phone: str,
    template_id: str,
) -> str:
    """Generate a cryptographically secure 6-digit OTP, cache it in Redis, and send via SMS."""
    code = "".join(secrets.choice("0123456789") for _ in range(6))

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
    db: AsyncSession, phone: str, page: int = 1, size: int = 20
) -> list[SmsRecord]:
    offset = (page - 1) * size
    result = await db.execute(
        select(SmsRecord)
        .where(SmsRecord.phone == phone)
        .order_by(SmsRecord.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    return list(result.scalars().all())


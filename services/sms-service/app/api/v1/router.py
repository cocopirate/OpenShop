from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.masking import mask_phone
from app.core.metrics import sms_rate_limit_triggered_total
from app.core.rate_limiter import check_ip_rate_limit, check_phone_rate_limit
from app.core.redis import get_redis
from app.models.sms_record import SmsStatus
from app.schemas.sms import (
    RateLimitErrorResponse,
    SmsSendRequest,
    SmsSendResponse,
    SmsRecordListResponse,
    SmsRecordOut,
    SmsVerifyRequest,
    SmsVerifyResponse,
)
from app.services.sms_service import (
    get_sms_records,
    send_sms,
    send_verification_code,
    verify_code,
)

router = APIRouter()
log = structlog.get_logger(__name__)

_MAX_PAGE_SIZE = 100


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post(
    "/send",
    response_model=SmsSendResponse,
    status_code=status.HTTP_201_CREATED,
    summary="发送短信",
    responses={429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"}},
)
async def send_sms_endpoint(
    req: SmsSendRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    redis = get_redis()
    ip = _get_client_ip(request)

    phone_rl = await check_phone_rate_limit(redis, req.phone)
    if not phone_rl.allowed:
        sms_rate_limit_triggered_total.labels(dimension="phone").inc()
        log.warning(
            "sms.rate_limit.phone",
            phone_masked=mask_phone(req.phone),
            retry_after=phone_rl.retry_after,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error_code": "RATE_LIMIT_EXCEEDED",
                "message": f"Phone rate limit exceeded. Retry after {phone_rl.retry_after}s",
                "retry_after": phone_rl.retry_after,
                "limit": phone_rl.limit,
                "window": phone_rl.window,
            },
            headers={"Retry-After": str(phone_rl.retry_after)},
        )

    ip_rl = await check_ip_rate_limit(redis, ip)
    if not ip_rl.allowed:
        sms_rate_limit_triggered_total.labels(dimension="ip").inc()
        log.warning("sms.rate_limit.ip", ip=ip, retry_after=ip_rl.retry_after)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error_code": "RATE_LIMIT_EXCEEDED",
                "message": f"IP rate limit exceeded. Retry after {ip_rl.retry_after}s",
                "retry_after": ip_rl.retry_after,
                "limit": ip_rl.limit,
                "window": ip_rl.window,
            },
            headers={"Retry-After": str(ip_rl.retry_after)},
        )

    record = await send_sms(db, req.phone, req.template_id, req.params, req.request_id)
    return SmsSendResponse(
        message_id=str(record.id),
        request_id=record.request_id,
        status=record.status,
        provider=record.provider,
        phone_masked=record.phone_masked or mask_phone(record.phone),
    )


@router.post(
    "/send-code",
    status_code=status.HTTP_201_CREATED,
    summary="发送验证码短信",
)
async def send_code_endpoint(
    phone: str,
    template_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    redis = get_redis()
    ip = _get_client_ip(request)

    phone_rl = await check_phone_rate_limit(redis, phone)
    if not phone_rl.allowed:
        sms_rate_limit_triggered_total.labels(dimension="phone").inc()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error_code": "RATE_LIMIT_EXCEEDED",
                "message": f"Phone rate limit exceeded. Retry after {phone_rl.retry_after}s",
                "retry_after": phone_rl.retry_after,
                "limit": phone_rl.limit,
                "window": phone_rl.window,
            },
            headers={"Retry-After": str(phone_rl.retry_after)},
        )

    ip_rl = await check_ip_rate_limit(redis, ip)
    if not ip_rl.allowed:
        sms_rate_limit_triggered_total.labels(dimension="ip").inc()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error_code": "RATE_LIMIT_EXCEEDED",
                "message": f"IP rate limit exceeded. Retry after {ip_rl.retry_after}s",
                "retry_after": ip_rl.retry_after,
                "limit": ip_rl.limit,
                "window": ip_rl.window,
            },
            headers={"Retry-After": str(ip_rl.retry_after)},
        )

    await send_verification_code(db, phone, template_id)
    return {"message": "verification code sent"}


@router.get(
    "/records",
    response_model=SmsRecordListResponse,
    summary="查询发送记录（支持手机号/时间/状态过滤 + 分页）",
)
async def get_sms_records_endpoint(
    phone: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    status: Optional[SmsStatus] = None,
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    if size > _MAX_PAGE_SIZE:
        size = _MAX_PAGE_SIZE
    records, total = await get_sms_records(
        db, phone=phone, start_time=start_time, end_time=end_time, status=status, page=page, size=size
    )
    return SmsRecordListResponse(
        total=total,
        page=page,
        size=size,
        items=[SmsRecordOut.model_validate(r) for r in records],
    )


@router.post(
    "/verify",
    response_model=SmsVerifyResponse,
    summary="验证短信验证码",
)
async def verify_sms(req: SmsVerifyRequest):
    valid = await verify_code(req.phone, req.code)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid or expired verification code",
        )
    return SmsVerifyResponse(phone=req.phone, valid=True)



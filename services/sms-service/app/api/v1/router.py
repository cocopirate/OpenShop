from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.masking import mask_phone
from app.core.metrics import sms_rate_limit_triggered_total
from app.core.rate_limiter import check_ip_rate_limit, check_phone_rate_limit
from app.core.redis import get_redis
from app.core.response import (
    SMS_INVALID_CODE,
    SMS_RATE_LIMIT_EXCEEDED,
    SMS_SEND_FAILED,
    err,
    ok,
)
from app.models.sms_record import SmsStatus
from app.schemas.sms import (
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
    status_code=status.HTTP_201_CREATED,
    summary="发送短信",
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
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=err(
                SMS_RATE_LIMIT_EXCEEDED,
                f"Phone rate limit exceeded. Retry after {phone_rl.retry_after}s",
            ),
            headers={"Retry-After": str(phone_rl.retry_after)},
        )

    ip_rl = await check_ip_rate_limit(redis, ip)
    if not ip_rl.allowed:
        sms_rate_limit_triggered_total.labels(dimension="ip").inc()
        log.warning("sms.rate_limit.ip", ip=ip, retry_after=ip_rl.retry_after)
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=err(
                SMS_RATE_LIMIT_EXCEEDED,
                f"IP rate limit exceeded. Retry after {ip_rl.retry_after}s",
            ),
            headers={"Retry-After": str(ip_rl.retry_after)},
        )

    record = await send_sms(db, req.phone, req.template_id, req.params, req.request_id)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=ok(SmsSendResponse(
            message_id=str(record.id),
            request_id=record.request_id,
            status=record.status,
            provider=record.provider,
            phone_masked=record.phone_masked or mask_phone(record.phone),
        ).model_dump(mode="json")),
    )


@router.post(
    "/send-code",
    status_code=status.HTTP_201_CREATED,
    summary="发送验证码短信",
    tags=["public"],
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
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=err(
                SMS_RATE_LIMIT_EXCEEDED,
                f"Phone rate limit exceeded. Retry after {phone_rl.retry_after}s",
            ),
            headers={"Retry-After": str(phone_rl.retry_after)},
        )

    ip_rl = await check_ip_rate_limit(redis, ip)
    if not ip_rl.allowed:
        sms_rate_limit_triggered_total.labels(dimension="ip").inc()
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=err(
                SMS_RATE_LIMIT_EXCEEDED,
                f"IP rate limit exceeded. Retry after {ip_rl.retry_after}s",
            ),
            headers={"Retry-After": str(ip_rl.retry_after)},
        )

    try:
        record = await send_verification_code(db, phone, template_id)
    except RuntimeError as exc:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=err(SMS_SEND_FAILED, str(exc)),
        )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=ok(SmsSendResponse(
            message_id=str(record.id),
            request_id=record.request_id,
            status=record.status,
            provider=record.provider,
            phone_masked=record.phone_masked or mask_phone(record.phone),
        ).model_dump(mode="json")),
    )


@router.get(
    "/records",
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
    return JSONResponse(
        content=ok(SmsRecordListResponse(
            total=total,
            page=page,
            size=size,
            items=[SmsRecordOut.model_validate(r) for r in records],
        ).model_dump(mode="json")),
    )


@router.post(
    "/verify",
    summary="验证短信验证码",
)
async def verify_sms(req: SmsVerifyRequest):
    valid = await verify_code(req.phone, req.code)
    if not valid:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=err(SMS_INVALID_CODE, "invalid or expired verification code"),
        )
    return JSONResponse(
        content=ok(SmsVerifyResponse(phone=req.phone, valid=True).model_dump(mode="json")),
    )



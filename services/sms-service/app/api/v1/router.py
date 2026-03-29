from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.masking import mask_phone
from app.core.metrics import sms_rate_limit_triggered_total
from app.core.rate_limiter import check_ip_rate_limit, check_phone_rate_limit
from app.core.redis import get_redis
from app.core.response import (
    SMS_INVALID_CODE,
    SMS_RATE_LIMIT_EXCEEDED,
    SMS_RECORD_NOT_FOUND,
    SMS_SEND_FAILED,
    SMS_TEMPLATE_NOT_FOUND,
    err,
    ok,
)
from app.models.sms_record import SmsStatus
from app.schemas.sms import (
    SendCodeRequest,
    SmsConfigOut,
    SmsConfigUpdate,
    SmsSendRequest,
    SmsSendResponse,
    SmsRecordListResponse,
    SmsRecordOut,
    SmsTemplateCreate,
    SmsTemplateListResponse,
    SmsTemplateOut,
    SmsTemplateUpdate,
    SmsVerifyRequest,
    SmsVerifyResponse,
)
from app.services.admin_service import (
    create_template,
    delete_record,
    delete_template,
    get_sms_config,
    get_template,
    list_templates,
    update_sms_config,
    update_template,
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


async def verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> Optional[str]:
    """Validate X-API-Key and return the mapped channel name for routing.

    If SMS_CLIENT_KEYS is empty the check is skipped (auth disabled) and None
    is returned, falling back to the default provider.
    """
    if not settings.SMS_CLIENT_KEYS:
        return None
    if not x_api_key or x_api_key not in settings.SMS_CLIENT_KEYS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")
    return settings.SMS_CLIENT_KEYS[x_api_key]


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

    record = await send_sms(db, req.phone, req.template_id, req.params, req.request_id, req.channel)
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
    req: SendCodeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    channel: Optional[str] = Depends(verify_api_key),
):
    redis = get_redis()
    ip = _get_client_ip(request)

    phone_rl = await check_phone_rate_limit(redis, req.phone)
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
        record = await send_verification_code(db, req.phone, req.template_id, channel=channel)
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


@router.delete(
    "/records/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除短信发送记录",
    description="根据记录 ID 删除单条短信发送记录。",
)
async def delete_sms_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_record(db, record_id)
    if not deleted:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(SMS_RECORD_NOT_FOUND, f"SMS record {record_id} not found"),
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


# ---------------------------------------------------------------------------
# SMS Templates – CRUD
# ---------------------------------------------------------------------------


@router.get(
    "/templates",
    summary="查询短信模板列表",
    description="支持按供应商（provider）和启用状态（is_active）过滤，分页返回。",
)
async def list_sms_templates(
    provider: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    if size > _MAX_PAGE_SIZE:
        size = _MAX_PAGE_SIZE
    templates, total = await list_templates(db, provider=provider, is_active=is_active, page=page, size=size)
    return JSONResponse(
        content=ok(SmsTemplateListResponse(
            total=total,
            page=page,
            size=size,
            items=[SmsTemplateOut.model_validate(t) for t in templates],
        ).model_dump(mode="json")),
    )


@router.post(
    "/templates",
    status_code=status.HTTP_201_CREATED,
    summary="创建短信模板",
    description="创建一条新的短信模板记录，关联到指定供应商的模板 ID。",
)
async def create_sms_template(
    data: SmsTemplateCreate,
    db: AsyncSession = Depends(get_db),
):
    template = await create_template(db, data)
    await db.commit()
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=ok(SmsTemplateOut.model_validate(template).model_dump(mode="json")),
    )


@router.get(
    "/templates/{template_id}",
    summary="查询短信模板详情",
    description="根据模板 ID 获取单条短信模板详情。",
)
async def get_sms_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    template = await get_template(db, template_id)
    if template is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(SMS_TEMPLATE_NOT_FOUND, f"SMS template {template_id} not found"),
        )
    return JSONResponse(
        content=ok(SmsTemplateOut.model_validate(template).model_dump(mode="json")),
    )


@router.put(
    "/templates/{template_id}",
    summary="更新短信模板",
    description="局部更新短信模板字段（name / content / provider / is_active）。",
)
async def update_sms_template(
    template_id: int,
    data: SmsTemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    template = await update_template(db, template_id, data)
    if template is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(SMS_TEMPLATE_NOT_FOUND, f"SMS template {template_id} not found"),
        )
    await db.commit()
    return JSONResponse(
        content=ok(SmsTemplateOut.model_validate(template).model_dump(mode="json")),
    )


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除短信模板",
    description="根据模板 ID 删除短信模板记录。",
)
async def delete_sms_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_template(db, template_id)
    if not deleted:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(SMS_TEMPLATE_NOT_FOUND, f"SMS template {template_id} not found"),
        )
    await db.commit()


# ---------------------------------------------------------------------------
# SMS Configuration
# ---------------------------------------------------------------------------


@router.get(
    "/config",
    summary="查询短信服务配置",
    description=(
        "返回当前运行时的短信服务配置，包括供应商、熔断器参数、限频规则等。\n\n"
        "**注意**：此接口仅返回运行时内存中的配置值，不含敏感密钥（Access Key 等）。"
    ),
)
async def get_sms_config_endpoint():
    return JSONResponse(
        content=ok(SmsConfigOut.model_validate(get_sms_config()).model_dump(mode="json")),
    )


@router.put(
    "/config",
    summary="更新短信服务配置",
    description=(
        "动态更新短信服务运行时配置（如切换供应商、调整限频阈值、配置供应商凭据等）。\n\n"
        "变更立即生效并持久化到数据库，服务重启后自动恢复。"
    ),
)
async def update_sms_config_endpoint(data: SmsConfigUpdate, db: AsyncSession = Depends(get_db)):
    updated = await update_sms_config(data, db)
    return JSONResponse(
        content=ok(SmsConfigOut.model_validate(updated).model_dump(mode="json")),
    )

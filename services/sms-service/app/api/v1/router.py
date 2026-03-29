from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.masking import mask_phone
from app.core.metrics import sms_rate_limit_triggered_total
from app.core.rate_limiter import check_ip_rate_limit, check_phone_rate_limit
from app.core.redis import get_redis
from app.core.response import (
    SMS_CHANNEL_NOT_FOUND,
    SMS_CLIENT_KEY_NOT_FOUND,
    SMS_INVALID_CODE,
    SMS_POLICY_IN_USE,
    SMS_POLICY_NOT_FOUND,
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
    SmsChannelCreate,
    SmsChannelListResponse,
    SmsChannelOut,
    SmsChannelUpdate,
    SmsClientKeyCreate,
    SmsClientKeyListResponse,
    SmsClientKeyOut,
    SmsPolicyCreate,
    SmsPolicyListResponse,
    SmsPolicyOut,
    SmsPolicyUpdate,
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
    create_client_key,
    create_template,
    delete_channel,
    delete_client_key,
    delete_policy,
    delete_record,
    delete_template,
    get_channel,
    get_client_key_channel,
    get_policy,
    get_template,
    list_channels,
    list_client_keys,
    list_policies,
    list_templates,
    patch_channel,
    patch_policy,
    update_template,
    upsert_channel,
    upsert_policy,
)
from app.services.sms_service import (
    _resolve_channel_and_policy,
    get_sms_records,
    send_sms,
    send_verification_code,
    verify_code,
)

router = APIRouter()
log = structlog.get_logger(__name__)

_MAX_PAGE_SIZE = 100


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> Optional[str]:
    """Validate X-API-Key and return the mapped channel name for routing.

    If no client keys are registered the check is skipped (auth disabled) and
    None is returned, falling back to the default channel.
    """
    from app.services.admin_service import list_client_keys as _list_keys
    _, total = await _list_keys(db)
    if total == 0:
        return None
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    channel = await get_client_key_channel(db, x_api_key)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return channel


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

    # Resolve channel/policy to get rate-limit values
    _, policy = await _resolve_channel_and_policy(db, req.channel)

    phone_rl = await check_phone_rate_limit(
        redis, req.phone,
        per_minute=policy.rate_limit_phone_per_minute,
        per_day=policy.rate_limit_phone_per_day,
    )
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

    ip_rl = await check_ip_rate_limit(
        redis, ip,
        per_minute=policy.rate_limit_ip_per_minute,
        per_day=policy.rate_limit_ip_per_day,
    )
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

    _, policy = await _resolve_channel_and_policy(db, channel)

    phone_rl = await check_phone_rate_limit(
        redis, req.phone,
        per_minute=policy.rate_limit_phone_per_minute,
        per_day=policy.rate_limit_phone_per_day,
    )
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

    ip_rl = await check_ip_rate_limit(
        redis, ip,
        per_minute=policy.rate_limit_ip_per_minute,
        per_day=policy.rate_limit_ip_per_day,
    )
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
        record = await send_verification_code(db, req.phone, req.template_id, channel_name=channel)
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
# SMS Policies – CRUD
# ---------------------------------------------------------------------------


@router.get(
    "/policies",
    summary="查询策略列表",
    description="返回所有已配置的策略。",
)
async def list_policies_endpoint(db: AsyncSession = Depends(get_db)):
    items, total = await list_policies(db)
    return JSONResponse(
        content=ok(SmsPolicyListResponse(
            total=total,
            items=[SmsPolicyOut.model_validate(p) for p in items],
        ).model_dump(mode="json")),
    )


@router.post(
    "/policies",
    status_code=status.HTTP_201_CREATED,
    summary="创建策略",
    description="使用自动生成的 UUID 名称创建一个新策略（通常使用 PUT /policies/{name} 指定名称）。",
)
async def create_policy_endpoint(
    data: SmsPolicyCreate,
    db: AsyncSession = Depends(get_db),
):
    import uuid
    name = str(uuid.uuid4())
    policy = await upsert_policy(db, name, data)
    await db.commit()
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=ok(SmsPolicyOut.model_validate(policy).model_dump(mode="json")),
    )


@router.get(
    "/policies/{policy_name}",
    summary="查询策略详情",
)
async def get_policy_endpoint(policy_name: str, db: AsyncSession = Depends(get_db)):
    policy = await get_policy(db, policy_name)
    if policy is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(SMS_POLICY_NOT_FOUND, f"Policy '{policy_name}' not found"),
        )
    return JSONResponse(content=ok(SmsPolicyOut.model_validate(policy).model_dump(mode="json")))


@router.put(
    "/policies/{policy_name}",
    status_code=status.HTTP_201_CREATED,
    summary="创建或替换策略",
    description="以 policy_name 为 key 完整写入策略配置，若已存在则全量替换。",
)
async def upsert_policy_endpoint(
    policy_name: str,
    data: SmsPolicyCreate,
    db: AsyncSession = Depends(get_db),
):
    policy = await upsert_policy(db, policy_name, data)
    await db.commit()
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=ok(SmsPolicyOut.model_validate(policy).model_dump(mode="json")),
    )


@router.patch(
    "/policies/{policy_name}",
    summary="局部更新策略",
    description="仅更新提交的字段，未提交的字段保留原值。",
)
async def patch_policy_endpoint(
    policy_name: str,
    data: SmsPolicyUpdate,
    db: AsyncSession = Depends(get_db),
):
    policy = await patch_policy(db, policy_name, data)
    if policy is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(SMS_POLICY_NOT_FOUND, f"Policy '{policy_name}' not found"),
        )
    await db.commit()
    return JSONResponse(content=ok(SmsPolicyOut.model_validate(policy).model_dump(mode="json")))


@router.delete(
    "/policies/{policy_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除策略",
    description="删除策略。若该策略被渠道引用则返回 409。",
)
async def delete_policy_endpoint(
    policy_name: str,
    db: AsyncSession = Depends(get_db),
):
    deleted, in_use = await delete_policy(db, policy_name)
    if in_use:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=err(SMS_POLICY_IN_USE, f"Policy '{policy_name}' is referenced by one or more channels"),
        )
    if not deleted:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(SMS_POLICY_NOT_FOUND, f"Policy '{policy_name}' not found"),
        )
    await db.commit()


# ---------------------------------------------------------------------------
# SMS Channels – CRUD
# ---------------------------------------------------------------------------


@router.get(
    "/channels",
    summary="查询渠道列表",
    description="返回所有已配置的多租户渠道（access_key_secret 等敏感字段已脱敏）。",
)
async def list_channels_endpoint(db: AsyncSession = Depends(get_db)):
    items, total = await list_channels(db)
    return JSONResponse(
        content=ok(SmsChannelListResponse(
            total=total,
            items=items,
        ).model_dump(mode="json")),
    )


@router.get(
    "/channels/{channel_name}",
    summary="查询渠道详情",
)
async def get_channel_endpoint(channel_name: str, db: AsyncSession = Depends(get_db)):
    channel = await get_channel(db, channel_name)
    if channel is None:
        return JSONResponse(
            status_code=404,
            content=err(SMS_CHANNEL_NOT_FOUND, f"Channel '{channel_name}' not found"),
        )
    return JSONResponse(content=ok(channel.model_dump(mode="json")))


@router.put(
    "/channels/{channel_name}",
    status_code=201,
    summary="创建或替换渠道",
    description="以 channel_name 为 key 完整写入渠道配置，若已存在则全量替换。",
)
async def upsert_channel_endpoint(
    channel_name: str,
    data: SmsChannelCreate,
    db: AsyncSession = Depends(get_db),
):
    channel = await upsert_channel(db, channel_name, data)
    await db.commit()
    return JSONResponse(
        status_code=201,
        content=ok(channel.model_dump(mode="json")),
    )


@router.patch(
    "/channels/{channel_name}",
    summary="局部更新渠道",
    description="仅更新提交的字段，未提交的字段保留原值。",
)
async def patch_channel_endpoint(
    channel_name: str,
    data: SmsChannelUpdate,
    db: AsyncSession = Depends(get_db),
):
    channel = await patch_channel(db, channel_name, data)
    if channel is None:
        return JSONResponse(
            status_code=404,
            content=err(SMS_CHANNEL_NOT_FOUND, f"Channel '{channel_name}' not found"),
        )
    await db.commit()
    return JSONResponse(content=ok(channel.model_dump(mode="json")))


@router.delete(
    "/channels/{channel_name}",
    status_code=204,
    summary="删除渠道",
)
async def delete_channel_endpoint(
    channel_name: str,
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_channel(db, channel_name)
    if not deleted:
        return JSONResponse(
            status_code=404,
            content=err(SMS_CHANNEL_NOT_FOUND, f"Channel '{channel_name}' not found"),
        )
    await db.commit()


# ---------------------------------------------------------------------------
# SMS Client Keys – CRUD
# ---------------------------------------------------------------------------


@router.get(
    "/client-keys",
    summary="查询客户端 API Key 列表",
    description="返回所有 X-API-Key → 渠道名称 映射。",
)
async def list_client_keys_endpoint(db: AsyncSession = Depends(get_db)):
    items, total = await list_client_keys(db)
    return JSONResponse(
        content=ok(SmsClientKeyListResponse(total=total, items=items).model_dump(mode="json")),
    )


@router.post(
    "/client-keys",
    status_code=201,
    summary="创建客户端 API Key",
    description="新增或覆写一条 API Key → 渠道 映射；Key 已存在时更新渠道名称。",
)
async def create_client_key_endpoint(
    data: SmsClientKeyCreate,
    db: AsyncSession = Depends(get_db),
):
    key = await create_client_key(db, data)
    await db.commit()
    return JSONResponse(
        status_code=201,
        content=ok(SmsClientKeyOut.model_validate(key).model_dump(mode="json")),
    )


@router.delete(
    "/client-keys/{api_key}",
    status_code=204,
    summary="删除客户端 API Key",
)
async def delete_client_key_endpoint(
    api_key: str,
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_client_key(db, api_key)
    if not deleted:
        return JSONResponse(
            status_code=404,
            content=err(SMS_CLIENT_KEY_NOT_FOUND, "API key not found"),
        )
    await db.commit()

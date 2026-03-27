"""Admin endpoints for SMS management (records, templates, configuration).

These routes are prefixed with `/api/sms/admin` and are intended to be called
only by authenticated admin users. Authentication / authorisation is enforced
by the API Gateway (e.g. role-based access control) before requests reach this
service.
"""
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.sms_record import SmsStatus
from app.schemas.sms import (
    SmsConfigOut,
    SmsConfigUpdate,
    SmsRecordListResponse,
    SmsRecordOut,
    SmsTemplateCreate,
    SmsTemplateListResponse,
    SmsTemplateOut,
    SmsTemplateUpdate,
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
from app.services.sms_service import get_sms_records

admin_router = APIRouter(prefix="/admin", tags=["admin"])

log = structlog.get_logger(__name__)

_MAX_PAGE_SIZE = 100


# ---------------------------------------------------------------------------
# SMS Records – admin view
# ---------------------------------------------------------------------------


@admin_router.get(
    "/records",
    response_model=SmsRecordListResponse,
    summary="【管理】查询短信发送记录",
    description=(
        "支持按手机号（明文）、时间范围、状态过滤，结果按发送时间倒序分页返回。\n\n"
        "与公开接口不同，此接口返回完整的原始手机号（未脱敏），仅限管理员调用。"
    ),
)
async def admin_get_sms_records(
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


@admin_router.delete(
    "/records/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="【管理】删除短信发送记录",
    description="根据记录 ID 删除单条短信发送记录。",
)
async def admin_delete_sms_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_record(db, record_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SMS record {record_id} not found",
        )


# ---------------------------------------------------------------------------
# SMS Templates – CRUD
# ---------------------------------------------------------------------------


@admin_router.get(
    "/templates",
    response_model=SmsTemplateListResponse,
    summary="【管理】查询短信模板列表",
    description="支持按供应商（provider）和启用状态（is_active）过滤，分页返回。",
)
async def admin_list_templates(
    provider: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    if size > _MAX_PAGE_SIZE:
        size = _MAX_PAGE_SIZE
    templates, total = await list_templates(db, provider=provider, is_active=is_active, page=page, size=size)
    return SmsTemplateListResponse(
        total=total,
        page=page,
        size=size,
        items=[SmsTemplateOut.model_validate(t) for t in templates],
    )


@admin_router.post(
    "/templates",
    response_model=SmsTemplateOut,
    status_code=status.HTTP_201_CREATED,
    summary="【管理】创建短信模板",
    description="创建一条新的短信模板记录，关联到指定供应商的模板 ID。",
)
async def admin_create_template(
    data: SmsTemplateCreate,
    db: AsyncSession = Depends(get_db),
):
    template = await create_template(db, data)
    await db.commit()
    return template


@admin_router.get(
    "/templates/{template_id}",
    response_model=SmsTemplateOut,
    summary="【管理】查询短信模板详情",
    description="根据模板 ID 获取单条短信模板详情。",
)
async def admin_get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    template = await get_template(db, template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SMS template {template_id} not found",
        )
    return template


@admin_router.put(
    "/templates/{template_id}",
    response_model=SmsTemplateOut,
    summary="【管理】更新短信模板",
    description="局部更新短信模板字段（name / content / provider / is_active）。",
)
async def admin_update_template(
    template_id: int,
    data: SmsTemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    template = await update_template(db, template_id, data)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SMS template {template_id} not found",
        )
    await db.commit()
    return template


@admin_router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="【管理】删除短信模板",
    description="根据模板 ID 删除短信模板记录。",
)
async def admin_delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_template(db, template_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SMS template {template_id} not found",
        )
    await db.commit()


# ---------------------------------------------------------------------------
# SMS Configuration
# ---------------------------------------------------------------------------


@admin_router.get(
    "/config",
    response_model=SmsConfigOut,
    summary="【管理】查询短信服务配置",
    description=(
        "返回当前运行时的短信服务配置，包括供应商、熔断器参数、限频规则等。\n\n"
        "**注意**：此接口仅返回运行时内存中的配置值，不含敏感密钥（Access Key 等）。"
    ),
)
async def admin_get_config():
    return get_sms_config()


@admin_router.put(
    "/config",
    response_model=SmsConfigOut,
    summary="【管理】更新短信服务配置",
    description=(
        "动态更新短信服务运行时配置（如切换供应商、调整限频阈值等）。\n\n"
        "**注意**：变更仅在当前进程内立即生效，服务重启后将恢复至环境变量配置。"
        "如需永久生效，请同步修改环境变量并滚动重启服务。"
    ),
)
async def admin_update_config(data: SmsConfigUpdate):
    updated = update_sms_config(data)
    return updated

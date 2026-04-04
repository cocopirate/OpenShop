"""Lead order CRUD and state transition endpoints."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

import httpx
import structlog
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.events import publish_lead_submitted
from app.core.response import (
    INTERNAL_ERROR,
    INVALID_PRODUCT_IDS,
    LEAD_ALREADY_TERMINAL,
    LEAD_NOT_FOUND,
    err,
    ok,
)
from app.schemas.lead import (
    LeadCancel,
    LeadConvert,
    LeadCreate,
    LeadCreateResponse,
    LeadListResponse,
    LeadResponse,
    LeadStatusLogResponse,
)
from app.services import lead_service

router = APIRouter()
log = structlog.get_logger(__name__)


async def _validate_product_ids(product_ids: list[str]) -> bool:
    """Call product-service to validate product IDs. Returns True if all valid."""
    if not product_ids:
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{settings.PRODUCT_SERVICE_URL}/internal/products/validate",
                json={"product_ids": product_ids},
            )
            return resp.status_code == 200
    except Exception as exc:
        log.warning("product_validation.failed", error=str(exc))
        # Fail open: allow submission if product-service is unavailable
        return True


# --------------------------------------------------------------------------- #
# User-side endpoints                                                           #
# --------------------------------------------------------------------------- #


@router.post("", status_code=status.HTTP_201_CREATED, summary="提交客资表单")
async def create_lead(
    body: LeadCreate,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Submit a lead form. Returns existing lead within 1-minute idempotency window."""
    valid = await _validate_product_ids(body.product_ids)
    if not valid:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=err(INVALID_PRODUCT_IDS, "One or more product IDs are invalid"),
        )

    lead, created = await lead_service.create_lead(db, body)

    if created:
        try:
            await publish_lead_submitted(
                lead_id=lead.id,
                phone=lead.phone,
                product_ids=lead.product_ids,
                created_at=lead.created_at,
            )
        except Exception as exc:
            log.error("lead.event_publish_failed", lead_id=str(lead.id), error=str(exc))

    response_data = LeadCreateResponse.model_validate(lead).model_dump(mode="json")
    http_status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return JSONResponse(
        status_code=http_status_code,
        content=ok(response_data),
    )


@router.get("", summary="查询客资列表")
async def list_leads(
    consumer_id: Optional[UUID] = Query(None, description="Filter by consumer ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    city: Optional[str] = Query(None, description="Filter by city"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """List leads with optional filters. Phone numbers are masked in the response."""
    leads, total = await lead_service.list_leads(
        db,
        consumer_id=consumer_id,
        status=status_filter,
        city=city,
        page=page,
        size=size,
    )
    items = []
    for lead in leads:
        item = LeadListResponse.model_validate(lead).model_dump(mode="json")
        item["phone"] = LeadListResponse.mask_phone(lead.phone)
        items.append(item)

    return JSONResponse(
        content=ok(
            {
                "items": items,
                "total": total,
                "page": page,
                "size": size,
            }
        )
    )


@router.get("/{lead_id}", summary="查询客资详情")
async def get_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Get lead details by ID."""
    lead = await lead_service.get_lead(db, lead_id)
    if lead is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(LEAD_NOT_FOUND, "Lead not found"),
        )
    return JSONResponse(
        content=ok(LeadResponse.model_validate(lead).model_dump(mode="json"))
    )


@router.patch("/{lead_id}/cancel", summary="取消客资")
async def cancel_lead(
    lead_id: UUID,
    body: LeadCancel = LeadCancel(),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Cancel a pending lead (user or merchant)."""
    try:
        lead = await lead_service.cancel_lead(
            db,
            lead_id,
            body,
            operator_type="consumer",
        )
    except ValueError:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=err(LEAD_ALREADY_TERMINAL, "Lead is already in a terminal status and cannot be modified"),
        )

    if lead is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(LEAD_NOT_FOUND, "Lead not found"),
        )
    return JSONResponse(
        content=ok(LeadResponse.model_validate(lead).model_dump(mode="json"))
    )


# --------------------------------------------------------------------------- #
# Merchant-side endpoints                                                       #
# --------------------------------------------------------------------------- #


@router.patch("/{lead_id}/convert", summary="标记已转化")
async def convert_lead(
    lead_id: UUID,
    body: LeadConvert = LeadConvert(),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Mark a lead as converted (merchant action)."""
    try:
        lead = await lead_service.convert_lead(
            db,
            lead_id,
            body,
            operator_type="merchant",
        )
    except ValueError:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=err(LEAD_ALREADY_TERMINAL, "Lead is already in a terminal status and cannot be modified"),
        )

    if lead is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(LEAD_NOT_FOUND, "Lead not found"),
        )
    return JSONResponse(
        content=ok(LeadResponse.model_validate(lead).model_dump(mode="json"))
    )


@router.get("/{lead_id}/logs", summary="查询状态变更日志")
async def get_lead_logs(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Get status change logs for a lead."""
    lead = await lead_service.get_lead(db, lead_id)
    if lead is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(LEAD_NOT_FOUND, "Lead not found"),
        )
    logs = await lead_service.get_lead_logs(db, lead_id)
    items = [LeadStatusLogResponse.model_validate(log_entry).model_dump(mode="json") for log_entry in logs]
    return JSONResponse(content=ok(items))

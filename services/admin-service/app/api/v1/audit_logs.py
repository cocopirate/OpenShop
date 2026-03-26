from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ok
from app.schemas.audit_log import AuditLogResponse
from app.services import audit_service

router = APIRouter()


@router.get("")
async def list_audit_logs(
    admin_id: Optional[int] = Query(None, description="Filter by admin ID"),
    target_type: Optional[str] = Query(None, description="Filter by target type (merchant/order/rider)"),
    date_from: Optional[datetime] = Query(None, description="Filter from date (ISO 8601)"),
    date_to: Optional[datetime] = Query(None, description="Filter to date (ISO 8601)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    logs, total = await audit_service.get_audit_logs(
        db,
        admin_id=admin_id,
        target_type=target_type,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return JSONResponse(
        content=ok(
            {
                "items": [AuditLogResponse.model_validate(lg).model_dump(mode="json") for lg in logs],
                "total": total,
                "page": page,
                "page_size": page_size,
            }
        )
    )

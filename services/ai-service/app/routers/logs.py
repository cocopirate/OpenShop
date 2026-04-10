"""Call log query and statistics endpoints."""
from __future__ import annotations

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.call_log import CallLog
from app.schemas import CallLogListResponse, CallLogResponse, LogStatsResponse, ServiceStats, TemplateStats

log = structlog.get_logger(__name__)

router = APIRouter()


@router.get("", response_model=CallLogListResponse)
async def list_logs(
    caller_service: str | None = Query(default=None),
    template_key: str | None = Query(default=None),
    status: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CallLog)

    if caller_service:
        stmt = stmt.where(CallLog.caller_service == caller_service)
    if template_key:
        stmt = stmt.where(CallLog.template_key == template_key)
    if status:
        stmt = stmt.where(CallLog.status == status)
    if date_from:
        stmt = stmt.where(CallLog.created_at >= date_from)
    if date_to:
        stmt = stmt.where(CallLog.created_at <= date_to)

    count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = count_result.scalar_one()

    stmt = stmt.order_by(CallLog.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return CallLogListResponse(
        items=[CallLogResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=LogStatsResponse)
async def get_log_stats(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    base_stmt = select(CallLog)
    if date_from:
        base_stmt = base_stmt.where(CallLog.created_at >= date_from)
    if date_to:
        base_stmt = base_stmt.where(CallLog.created_at <= date_to)

    subq = base_stmt.subquery()

    # Stats by service
    svc_stmt = (
        select(
            subq.c.caller_service,
            func.count().label("total_calls"),
            func.avg(
                func.cast(subq.c.status == "success", func.Integer())
            ).label("success_rate"),
            func.coalesce(func.sum(subq.c.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(subq.c.estimated_cost_usd), 0).label("estimated_cost_usd"),
            func.coalesce(func.avg(subq.c.duration_ms), 0).label("avg_duration_ms"),
        )
        .group_by(subq.c.caller_service)
    )
    svc_result = await db.execute(svc_stmt)
    by_service = [
        ServiceStats(
            caller_service=row.caller_service,
            total_calls=row.total_calls,
            success_rate=float(row.success_rate or 0),
            total_tokens=int(row.total_tokens),
            estimated_cost_usd=float(row.estimated_cost_usd),
            avg_duration_ms=float(row.avg_duration_ms or 0),
        )
        for row in svc_result
    ]

    # Stats by template
    tpl_stmt = (
        select(
            subq.c.template_key,
            func.count().label("total_calls"),
            func.avg(
                func.cast(subq.c.cache_hit.is_(True), func.Integer())
            ).label("cache_hit_rate"),
        )
        .where(subq.c.template_key.isnot(None))
        .group_by(subq.c.template_key)
    )
    tpl_result = await db.execute(tpl_stmt)
    by_template = [
        TemplateStats(
            template_key=row.template_key,
            total_calls=row.total_calls,
            cache_hit_rate=float(row.cache_hit_rate or 0),
        )
        for row in tpl_result
    ]

    period_parts = []
    if date_from:
        period_parts.append(date_from.strftime("%Y-%m-%d"))
    if date_to:
        period_parts.append(date_to.strftime("%Y-%m-%d"))
    period = " ~ ".join(period_parts) if period_parts else "all time"

    return LogStatsResponse(period=period, by_service=by_service, by_template=by_template)

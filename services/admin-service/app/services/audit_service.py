from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AdminOperationLog
from app.schemas.audit_log import AuditLogCreate


async def create_audit_log(db: AsyncSession, data: AuditLogCreate) -> AdminOperationLog:
    log = AdminOperationLog(
        admin_id=data.admin_id,
        admin_name=data.admin_name,
        action=data.action,
        target_type=data.target_type,
        target_id=data.target_id,
        request_body=data.request_body,
        ip=data.ip,
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log


async def get_audit_logs(
    db: AsyncSession,
    admin_id: Optional[int] = None,
    target_type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[AdminOperationLog], int]:
    query = select(AdminOperationLog)
    count_query = select(func.count()).select_from(AdminOperationLog)

    if admin_id is not None:
        query = query.where(AdminOperationLog.admin_id == admin_id)
        count_query = count_query.where(AdminOperationLog.admin_id == admin_id)
    if target_type is not None:
        query = query.where(AdminOperationLog.target_type == target_type)
        count_query = count_query.where(AdminOperationLog.target_type == target_type)
    if date_from is not None:
        query = query.where(AdminOperationLog.created_at >= date_from)
        count_query = count_query.where(AdminOperationLog.created_at >= date_from)
    if date_to is not None:
        query = query.where(AdminOperationLog.created_at <= date_to)
        count_query = count_query.where(AdminOperationLog.created_at <= date_to)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(AdminOperationLog.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    return list(result.scalars().all()), total

"""Business logic for lead order management."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import LeadOrder, LeadStatusLog
from app.schemas.lead import LeadCancel, LeadConvert, LeadCreate

TERMINAL_STATUSES = {"converted", "cancelled"}


async def create_lead(
    db: AsyncSession,
    data: LeadCreate,
    *,
    consumer_id: Optional[UUID] = None,
) -> tuple[LeadOrder, bool]:
    """Create a new lead or return existing one if within idempotency window.

    Returns (lead, created) where created=False means an existing lead was returned.
    """
    effective_consumer_id = consumer_id or data.consumer_id

    # Idempotency: same phone + sorted product_ids within 1 minute
    one_minute_ago = datetime.now(timezone.utc) - timedelta(minutes=1)
    sorted_ids = sorted(data.product_ids)

    result = await db.execute(
        select(LeadOrder).where(
            and_(
                LeadOrder.phone == data.phone,
                LeadOrder.created_at >= one_minute_ago,
                LeadOrder.status == "pending",
            )
        )
    )
    existing_leads = result.scalars().all()
    for lead in existing_leads:
        if sorted(lead.product_ids) == sorted_ids:
            return lead, False

    lead = LeadOrder(
        phone=data.phone,
        city=data.city,
        district=data.district,
        product_ids=data.product_ids,
        remark=data.remark,
        status="pending",
        source=data.source,
        consumer_id=effective_consumer_id,
    )
    db.add(lead)
    await db.flush()
    await db.refresh(lead)
    return lead, True


async def get_lead(db: AsyncSession, lead_id: UUID) -> Optional[LeadOrder]:
    result = await db.execute(select(LeadOrder).where(LeadOrder.id == lead_id))
    return result.scalar_one_or_none()


async def list_leads(
    db: AsyncSession,
    *,
    consumer_id: Optional[UUID] = None,
    status: Optional[str] = None,
    city: Optional[str] = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[LeadOrder], int]:
    """Return (leads, total) with optional filters."""
    conditions = []
    if consumer_id is not None:
        conditions.append(LeadOrder.consumer_id == consumer_id)
    if status is not None:
        conditions.append(LeadOrder.status == status)
    if city is not None:
        conditions.append(LeadOrder.city == city)

    count_q = select(LeadOrder)
    if conditions:
        count_q = count_q.where(and_(*conditions))

    total_result = await db.execute(count_q)
    total = len(total_result.scalars().all())

    q = count_q.offset((page - 1) * size).limit(size).order_by(LeadOrder.created_at.desc())
    result = await db.execute(q)
    return result.scalars().all(), total


async def convert_lead(
    db: AsyncSession,
    lead_id: UUID,
    data: LeadConvert,
    *,
    operator_id: Optional[UUID] = None,
    operator_type: str = "merchant",
) -> Optional[LeadOrder]:
    """Mark a lead as converted. Returns None if not found or already terminal."""
    lead = await get_lead(db, lead_id)
    if lead is None:
        return None
    if lead.status in TERMINAL_STATUSES:
        raise ValueError(f"Lead is already in terminal status: {lead.status}")

    old_status = lead.status
    lead.status = "converted"
    if data.converted_order_id is not None:
        lead.converted_order_id = data.converted_order_id

    log_entry = LeadStatusLog(
        lead_id=lead.id,
        from_status=old_status,
        to_status="converted",
        operator_id=operator_id,
        operator_type=operator_type,
        note=data.note,
    )
    db.add(log_entry)
    await db.flush()
    await db.refresh(lead)
    return lead


async def cancel_lead(
    db: AsyncSession,
    lead_id: UUID,
    data: LeadCancel,
    *,
    operator_id: Optional[UUID] = None,
    operator_type: str = "consumer",
) -> Optional[LeadOrder]:
    """Mark a lead as cancelled. Returns None if not found or already terminal."""
    lead = await get_lead(db, lead_id)
    if lead is None:
        return None
    if lead.status in TERMINAL_STATUSES:
        raise ValueError(f"Lead is already in terminal status: {lead.status}")

    old_status = lead.status
    lead.status = "cancelled"

    log_entry = LeadStatusLog(
        lead_id=lead.id,
        from_status=old_status,
        to_status="cancelled",
        operator_id=operator_id,
        operator_type=operator_type,
        note=data.note,
    )
    db.add(log_entry)
    await db.flush()
    await db.refresh(lead)
    return lead


async def get_lead_logs(db: AsyncSession, lead_id: UUID) -> list[LeadStatusLog]:
    result = await db.execute(
        select(LeadStatusLog)
        .where(LeadStatusLog.lead_id == lead_id)
        .order_by(LeadStatusLog.created_at.asc())
    )
    return result.scalars().all()

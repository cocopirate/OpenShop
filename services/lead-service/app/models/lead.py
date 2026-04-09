"""ORM models for lead order management."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    pass


class LeadOrder(Base):
    __tablename__ = "lead_order"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(64), nullable=False)
    district: Mapped[str] = mapped_column(String(64), nullable=False)
    product_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("pending", "converted", "cancelled", name="leadstatus"),
        nullable=False,
        server_default="pending",
        index=True,
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    consumer_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    converted_order_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    status_logs: Mapped[list[LeadStatusLog]] = relationship(
        "LeadStatusLog", back_populates="lead", cascade="all, delete-orphan"
    )


class LeadStatusLog(Base):
    __tablename__ = "lead_status_log"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("lead_order.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[str] = mapped_column(
        Enum("pending", "converted", "cancelled", name="leadstatus"),
        nullable=False,
    )
    to_status: Mapped[str] = mapped_column(
        Enum("pending", "converted", "cancelled", name="leadstatus"),
        nullable=False,
    )
    operator_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    operator_type: Mapped[str] = mapped_column(
        Enum("consumer", "merchant", "system", name="leadoperatortype"),
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    lead: Mapped[LeadOrder] = relationship("LeadOrder", back_populates="status_logs")

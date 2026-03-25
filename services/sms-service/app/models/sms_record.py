import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SmsStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class SmsRecord(Base):
    __tablename__ = "sms_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    phone_masked: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    template_id: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[SmsStatus] = mapped_column(
        Enum(SmsStatus), nullable=False, default=SmsStatus.PENDING
    )
    error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_sms_records_phone_created_at", "phone", "created_at"),
    )

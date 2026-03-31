"""ORM model for product SPU (Standard Product Unit)."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SpuStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


class Spu(Base):
    __tablename__ = "product_spu"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    brand_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[SpuStatus] = mapped_column(
        Enum(SpuStatus, name="spu_status"), nullable=False, default=SpuStatus.DRAFT
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

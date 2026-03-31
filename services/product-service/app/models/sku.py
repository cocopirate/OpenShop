"""ORM model for product SKU (Stock Keeping Unit)."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SkuStatus(str, enum.Enum):
    ENABLE = "ENABLE"
    DISABLE = "DISABLE"


class Sku(Base):
    __tablename__ = "product_sku"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    spu_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    attributes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[SkuStatus] = mapped_column(
        Enum(SkuStatus, name="sku_status"), nullable=False, default=SkuStatus.ENABLE
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

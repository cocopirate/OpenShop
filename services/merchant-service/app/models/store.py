from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from sqlalchemy import BigInteger, DateTime, Numeric, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class MerchantStore(Base):
    __tablename__ = "merchant_store"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    merchant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    store_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lat: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    lng: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

from __future__ import annotations
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class MerchantStaff(Base):
    __tablename__ = "merchant_staff"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    merchant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    store_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    real_name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    job_type: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

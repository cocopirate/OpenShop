"""ORM model for merchant sub-account."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, SmallInteger, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MerchantSubAccount(Base):
    __tablename__ = "merchant_sub_account"
    __table_args__ = (UniqueConstraint("merchant_id", "username"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    merchant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    real_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

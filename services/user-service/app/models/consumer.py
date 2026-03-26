"""ORM models for consumer account management."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

import uuid6
from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ConsumerAccount(Base):
    __tablename__ = "consumer_account"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), unique=True, nullable=False, index=True, default=uuid6.uuid7
    )
    nickname: Mapped[str | None] = mapped_column(String(50), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)
    gender: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    birthday: Mapped[date | None] = mapped_column(Date, nullable=True)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    addresses: Mapped[list[ConsumerAddress]] = relationship(
        "ConsumerAddress", back_populates="consumer", cascade="all, delete-orphan"
    )


class ConsumerAddress(Base):
    __tablename__ = "consumer_address"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    consumer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("consumer_account.id", ondelete="CASCADE"), nullable=False, index=True
    )
    receiver: Mapped[str | None] = mapped_column(String(50), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    province: Mapped[str | None] = mapped_column(String(50), nullable=True)
    city: Mapped[str | None] = mapped_column(String(50), nullable=True)
    district: Mapped[str | None] = mapped_column(String(50), nullable=True)
    detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_default: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    consumer: Mapped[ConsumerAccount] = relationship("ConsumerAccount", back_populates="addresses")

"""ORM models for product groups and group-product relationships."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GroupType(str, enum.Enum):
    MANUAL = "MANUAL"
    RULE = "RULE"


class GroupStatus(str, enum.Enum):
    ENABLE = "ENABLE"
    DISABLE = "DISABLE"


class ProductGroup(Base):
    __tablename__ = "product_group"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[GroupType] = mapped_column(
        Enum(GroupType, name="group_type"), nullable=False, default=GroupType.MANUAL
    )
    status: Mapped[GroupStatus] = mapped_column(
        Enum(GroupStatus, name="group_status"), nullable=False, default=GroupStatus.ENABLE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )


class ProductGroupItem(Base):
    __tablename__ = "product_group_item"

    group_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product_group.id"), primary_key=True
    )
    spu_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("group_id", "spu_id", name="uq_group_spu"),
    )

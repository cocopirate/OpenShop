from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import uuid6
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, SmallInteger, String, Table, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.role import AdminRole

admin_account_role = Table(
    "admin_account_role",
    Base.metadata,
    Column("admin_id", BigInteger, ForeignKey("admin_account.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", BigInteger, ForeignKey("admin_role.id", ondelete="CASCADE"), primary_key=True),
)


class AdminAccount(Base):
    __tablename__ = "admin_account"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), unique=True, nullable=False, index=True, default=uuid6.uuid7
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    real_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # 1=active, 0=disabled
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="1")
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_login_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    roles: Mapped[list[AdminRole]] = relationship(
        "AdminRole", secondary="admin_account_role", back_populates="admins"
    )

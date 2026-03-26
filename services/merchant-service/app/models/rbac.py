"""ORM models for merchant RBAC: roles, permissions, and assignment tables."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    SmallInteger,
    String,
    Table,
    Column,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.merchant import MerchantAccount

# Association table: role ↔ permission (M2M)
merchant_role_permission = Table(
    "merchant_role_permission",
    Base.metadata,
    Column(
        "role_id",
        BigInteger,
        ForeignKey("merchant_role.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_id",
        BigInteger,
        ForeignKey("merchant_permission.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

# Association table: account ↔ role (3-column composite PK)
merchant_account_role = Table(
    "merchant_account_role",
    Base.metadata,
    Column("account_id", BigInteger, nullable=False, primary_key=True),
    Column("account_type", SmallInteger, nullable=False, primary_key=True),
    Column(
        "role_id",
        BigInteger,
        ForeignKey("merchant_role.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    ),
)


class MerchantRole(Base):
    __tablename__ = "merchant_role"
    __table_args__ = (UniqueConstraint("merchant_id", "role_code"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    merchant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    role_code: Mapped[str] = mapped_column(String(50), nullable=False)
    role_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_system: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    merchant: Mapped[MerchantAccount] = relationship("MerchantAccount", back_populates="roles")
    permissions: Mapped[list[MerchantPermission]] = relationship(
        "MerchantPermission", secondary=merchant_role_permission, back_populates="roles"
    )


class MerchantPermission(Base):
    __tablename__ = "merchant_permission"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    perm_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    perm_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    perm_type: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    roles: Mapped[list[MerchantRole]] = relationship(
        "MerchantRole", secondary=merchant_role_permission, back_populates="permissions"
    )

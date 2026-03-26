from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Column, ForeignKey, SmallInteger, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.admin import AdminAccount
    from app.models.permission import AdminPermission

admin_role_permission = Table(
    "admin_role_permission",
    Base.metadata,
    Column("role_id", BigInteger, ForeignKey("admin_role.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "permission_id",
        BigInteger,
        ForeignKey("admin_permission.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class AdminRole(Base):
    __tablename__ = "admin_role"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    role_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    role_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # 1=system preset role, 0=custom
    is_system: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    # 1=active, 0=disabled
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="1")

    permissions: Mapped[list[AdminPermission]] = relationship(
        "AdminPermission", secondary="admin_role_permission", back_populates="roles"
    )
    admins: Mapped[list[AdminAccount]] = relationship(
        "AdminAccount", secondary="admin_account_role", back_populates="roles"
    )

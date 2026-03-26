from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.role import AdminRole


class AdminPermission(Base):
    __tablename__ = "admin_permission"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    parent_id: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    perm_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    perm_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # 1=menu 2=button 3=api
    perm_type: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    method: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    roles: Mapped[list[AdminRole]] = relationship(
        "AdminRole", secondary="admin_role_permission", back_populates="permissions"
    )

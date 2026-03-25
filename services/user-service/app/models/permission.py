from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.role import Role


class PermissionType(str, enum.Enum):
    menu = "menu"
    api = "api"


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    type: Mapped[PermissionType] = mapped_column(Enum(PermissionType), nullable=False)
    method: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    path: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("permissions.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    roles: Mapped[list[Role]] = relationship(
        "Role", secondary="role_permissions", back_populates="permissions"
    )

"""ORM models for product attributes and category-attribute bindings."""
from __future__ import annotations

import enum

from sqlalchemy import BigInteger, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AttributeType(str, enum.Enum):
    SALE = "SALE"
    SPEC = "SPEC"


class Attribute(Base):
    __tablename__ = "product_attribute"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[AttributeType] = mapped_column(
        Enum(AttributeType, name="attribute_type"), nullable=False, default=AttributeType.SPEC
    )


class CategoryAttribute(Base):
    __tablename__ = "product_category_attribute"

    category_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product_category.id"), primary_key=True
    )
    attribute_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product_attribute.id"), primary_key=True
    )

    __table_args__ = (
        UniqueConstraint("category_id", "attribute_id", name="uq_category_attribute"),
    )

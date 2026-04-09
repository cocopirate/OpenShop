from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SeoPage(Base):
    __tablename__ = "seo_page"
    __table_args__ = (
        UniqueConstraint("city_id", "district_id", "service_id", name="uq_seo_page_combination"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("city.id"), nullable=False, index=True)
    district_id: Mapped[int] = mapped_column(ForeignKey("district.id"), nullable=False, index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("service.id"), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    h1: Mapped[str | None] = mapped_column(String, nullable=True)
    content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String, server_default="draft", nullable=False, index=True)
    generation_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    city: Mapped["City"] = relationship("City", back_populates="seo_pages")  # noqa: F821
    district: Mapped["District"] = relationship("District", back_populates="seo_pages")  # noqa: F821
    service: Mapped["Service"] = relationship("Service", back_populates="seo_pages")  # noqa: F821

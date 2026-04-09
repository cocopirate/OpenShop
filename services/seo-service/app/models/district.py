from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class District(Base):
    __tablename__ = "district"
    __table_args__ = (UniqueConstraint("city_id", "slug", name="uq_district_city_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("city.id"), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    landmarks: Mapped[list] = mapped_column(JSONB, server_default="'[]'", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    city: Mapped["City"] = relationship("City", back_populates="districts")  # noqa: F821
    seo_pages: Mapped[list["SeoPage"]] = relationship("SeoPage", back_populates="district")  # noqa: F821

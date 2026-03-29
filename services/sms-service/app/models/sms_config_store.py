from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SmsConfigStore(Base):
    """Single-row JSON config store for persisting SMS runtime configuration.

    Row id=1 holds the full config blob. On startup the service applies this
    over the env-var defaults so the service can be fully configured via API
    without relying on environment variables after initial bootstrap.
    """

    __tablename__ = "sms_config_store"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

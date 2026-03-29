from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SmsClientKey(Base):
    """客户端 API Key → 渠道名称 映射表。

    取代原来存储在 settings.SMS_CLIENT_KEYS 中的映射。
    """

    __tablename__ = "sms_client_keys"

    api_key: Mapped[str] = mapped_column(String(128), primary_key=True, nullable=False)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

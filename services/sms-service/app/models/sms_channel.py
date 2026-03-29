from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SmsChannel(Base):
    """SMS渠道表：每行代表一个命名渠道，持有供应商凭据并关联一个策略。

    取代原来存储在 settings.SMS_CHANNELS JSON 中的配置。
    服务启动时，若表为空则自动创建名为 ``_default`` 的默认渠道。
    """

    __tablename__ = "sms_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="aliyun")
    # 关联策略名称；NULL 时使用 "default" 策略
    policy_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # Aliyun / AliyunPhoneSvc credentials
    access_key_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    access_key_secret: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    sign_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    endpoint: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    # ChuangLan credentials
    account: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    password: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    api_url: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    # Tencent credentials
    app_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    secret_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    secret_key: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SmsPolicy(Base):
    """SMS策略表：保存限频、验证码TTL、熔断参数等配置。

    每个 SmsChannel 通过 policy_name 关联到一个策略。
    服务启动时自动创建名为 ``default`` 的默认策略（若不存在）。
    """

    __tablename__ = "sms_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    code_ttl: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    rate_limit_phone_per_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    rate_limit_phone_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    rate_limit_ip_per_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    rate_limit_ip_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    records_retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    failure_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    recovery_timeout: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    fallback_channel: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

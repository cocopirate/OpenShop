from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuthCredential(Base):
    __tablename__ = "auth_credential"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # phone / email / username / wechat openid
    identity: Mapped[str] = mapped_column(String(100), nullable=False)
    # 1=phone 2=email 3=username 4=wechat
    identity_type: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # password hash / oauth token
    credential: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # 1=consumer 2=merchant 3=merchant_sub 4=staff 5=admin
    account_type: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # FK to the business entity table (consumer_id / merchant_id / etc.)
    biz_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # 1=active 0=disabled
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )


class AuthLoginLog(Base):
    __tablename__ = "auth_login_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    biz_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # 1=consumer 2=merchant 3=merchant_sub 4=staff 5=admin
    account_type: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    login_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    device_info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    login_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    # 1=success 0=failure
    result: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

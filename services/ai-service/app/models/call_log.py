"""SQLAlchemy model for call_log table."""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, Integer, Numeric, String, Text
from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class CallLog(Base):
    __tablename__ = "call_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    caller_service = Column(String, nullable=False)
    caller_ref_id = Column(String, nullable=True)
    template_key = Column(String, nullable=True)
    template_version = Column(Integer, nullable=True)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    estimated_cost_usd = Column(Numeric(10, 6), nullable=True)
    status = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    request_hash = Column(String, nullable=True)
    cache_hit = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

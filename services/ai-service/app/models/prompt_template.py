"""SQLAlchemy model for prompt_template table."""
from __future__ import annotations

from sqlalchemy import Boolean, Column, Float, Integer, String, Text
from sqlalchemy import DateTime
from sqlalchemy.sql import func

from app.database import Base


class PromptTemplate(Base):
    __tablename__ = "prompt_template"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, nullable=False)
    version = Column(Integer, nullable=False, server_default="1")
    is_active = Column(Boolean, nullable=False, server_default="true")
    provider = Column(String, nullable=False, server_default="openai")
    model = Column(String, nullable=True)
    system_prompt = Column(Text, nullable=False)
    user_prompt_template = Column(Text, nullable=False)
    temperature = Column(Float, nullable=False, server_default="0.7")
    max_tokens = Column(Integer, nullable=False, server_default="1000")
    response_format = Column(String, nullable=False, server_default="text")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

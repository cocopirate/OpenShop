from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.sms_record import SmsStatus


class SmsSendRequest(BaseModel):
    phone: str = Field(..., description="E.164 or local format phone number")
    template_id: str = Field(..., description="SMS template identifier")
    params: dict = Field(default_factory=dict, description="Template variable substitutions")


class SmsSendResponse(BaseModel):
    message_id: str
    status: SmsStatus
    provider: str


class SmsVerifyRequest(BaseModel):
    phone: str
    code: str


class SmsVerifyResponse(BaseModel):
    phone: str
    valid: bool


class SmsRecordOut(BaseModel):
    id: int
    phone: str
    template_id: str
    provider: str
    provider_message_id: Optional[str] = None
    status: SmsStatus
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

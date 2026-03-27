from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.sms_record import SmsStatus


class SmsSendRequest(BaseModel):
    phone: str = Field(..., description="E.164 or local format phone number")
    template_id: str = Field(..., description="SMS template identifier")
    params: dict = Field(default_factory=dict, description="Template variable substitutions")
    request_id: Optional[str] = Field(None, max_length=64, description="Client-provided idempotency key (max 64 chars)")


class SmsSendResponse(BaseModel):
    message_id: str
    request_id: Optional[str] = None
    status: SmsStatus
    provider: str
    phone_masked: str


class SmsVerifyRequest(BaseModel):
    phone: str
    code: str


class SmsVerifyResponse(BaseModel):
    phone: str
    valid: bool


class SmsRecordOut(BaseModel):
    id: int
    request_id: Optional[str] = None
    phone_masked: str
    template_id: str
    provider: str
    provider_message_id: Optional[str] = None
    status: SmsStatus
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SmsRecordListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: List[SmsRecordOut]


# ---------------------------------------------------------------------------
# Admin – SMS Template schemas
# ---------------------------------------------------------------------------


class SmsTemplateCreate(BaseModel):
    provider_template_id: str = Field(..., max_length=64, description="供应商模板 ID（如阿里云模板 Code）")
    name: str = Field(..., max_length=128, description="模板本地名称")
    content: str = Field(..., description="模板内容（含变量占位符）")
    provider: str = Field(..., max_length=32, description="所属供应商（aliyun / tencent / chuanglan）")
    is_active: bool = Field(True, description="是否启用")


class SmsTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128, description="模板本地名称")
    content: Optional[str] = Field(None, description="模板内容")
    provider: Optional[str] = Field(None, max_length=32, description="所属供应商")
    is_active: Optional[bool] = Field(None, description="是否启用")


class SmsTemplateOut(BaseModel):
    id: int
    provider_template_id: str
    name: str
    content: str
    provider: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SmsTemplateListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: List[SmsTemplateOut]


# ---------------------------------------------------------------------------
# Admin – SMS Configuration schemas
# ---------------------------------------------------------------------------


class SmsConfigOut(BaseModel):
    sms_provider: str = Field(..., description="当前活跃供应商")
    sms_provider_fallback: str = Field(..., description="备用供应商（空字符串表示无备用）")
    sms_provider_failure_threshold: int = Field(..., description="熔断器：连续失败次数阈值")
    sms_provider_recovery_timeout: int = Field(..., description="熔断器：恢复等待时间（秒）")
    sms_code_ttl: int = Field(..., description="验证码有效期（秒）")
    sms_rate_limit_phone_per_minute: int = Field(..., description="单手机号每分钟限频")
    sms_rate_limit_phone_per_day: int = Field(..., description="单手机号每日限频")
    sms_rate_limit_ip_per_minute: int = Field(..., description="单 IP 每分钟限频")
    sms_rate_limit_ip_per_day: int = Field(..., description="单 IP 每日限频")
    sms_records_retention_days: int = Field(..., description="发送记录保留天数（0 = 永久保留）")


class SmsConfigUpdate(BaseModel):
    sms_provider: Optional[str] = Field(None, description="切换活跃供应商")
    sms_provider_fallback: Optional[str] = Field(None, description="切换备用供应商")
    sms_provider_failure_threshold: Optional[int] = Field(None, ge=1, description="熔断阈值（≥1）")
    sms_provider_recovery_timeout: Optional[int] = Field(None, ge=1, description="熔断恢复等待时间（秒，≥1）")
    sms_code_ttl: Optional[int] = Field(None, ge=60, description="验证码有效期（秒，≥60）")
    sms_rate_limit_phone_per_minute: Optional[int] = Field(None, ge=1, description="单手机号每分钟限频（≥1）")
    sms_rate_limit_phone_per_day: Optional[int] = Field(None, ge=1, description="单手机号每日限频（≥1）")
    sms_rate_limit_ip_per_minute: Optional[int] = Field(None, ge=1, description="单 IP 每分钟限频（≥1）")
    sms_rate_limit_ip_per_day: Optional[int] = Field(None, ge=1, description="单 IP 每日限频（≥1）")
    sms_records_retention_days: Optional[int] = Field(None, ge=0, description="发送记录保留天数（≥0）")

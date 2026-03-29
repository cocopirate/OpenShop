from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.sms_record import SmsStatus


class SendCodeRequest(BaseModel):
    phone: str = Field(..., description="手机号")
    template_id: str = Field(..., description="验证码模板 ID")


class SmsSendRequest(BaseModel):
    phone: str = Field(..., description="E.164 or local format phone number")
    template_id: str = Field(..., description="SMS template identifier")
    params: dict = Field(default_factory=dict, description="Template variable substitutions")
    request_id: Optional[str] = Field(None, max_length=64, description="Client-provided idempotency key (max 64 chars)")
    channel: Optional[str] = Field(None, max_length=64, description="Named channel for routing (e.g. 'internal', 'biz_a'); defaults to the default channel")


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
# Admin – SMS Policy CRUD schemas
# ---------------------------------------------------------------------------


class SmsPolicyCreate(BaseModel):
    """创建或完整替换一个策略。"""
    code_ttl: int = Field(300, ge=60, description="验证码有效期（秒，≥60）")
    rate_limit_phone_per_minute: int = Field(1, ge=1, description="单手机号每分钟限频（≥1）")
    rate_limit_phone_per_day: int = Field(10, ge=1, description="单手机号每日限频（≥1）")
    rate_limit_ip_per_minute: int = Field(10, ge=1, description="单 IP 每分钟限频（≥1）")
    rate_limit_ip_per_day: int = Field(100, ge=1, description="单 IP 每日限频（≥1）")
    records_retention_days: int = Field(90, ge=0, description="发送记录保留天数（0 = 永久保留）")
    failure_threshold: int = Field(3, ge=1, description="熔断阈值（连续失败次数，≥1）")
    recovery_timeout: int = Field(60, ge=1, description="熔断恢复等待时间（秒，≥1）")
    fallback_channel: Optional[str] = Field(None, max_length=64, description="熔断后切换的备用渠道名称")


class SmsPolicyUpdate(BaseModel):
    """局部更新策略——仅更新提交的字段。"""
    code_ttl: Optional[int] = Field(None, ge=60, description="验证码有效期（秒，≥60）")
    rate_limit_phone_per_minute: Optional[int] = Field(None, ge=1, description="单手机号每分钟限频（≥1）")
    rate_limit_phone_per_day: Optional[int] = Field(None, ge=1, description="单手机号每日限频（≥1）")
    rate_limit_ip_per_minute: Optional[int] = Field(None, ge=1, description="单 IP 每分钟限频（≥1）")
    rate_limit_ip_per_day: Optional[int] = Field(None, ge=1, description="单 IP 每日限频（≥1）")
    records_retention_days: Optional[int] = Field(None, ge=0, description="发送记录保留天数（≥0）")
    failure_threshold: Optional[int] = Field(None, ge=1, description="熔断阈值（≥1）")
    recovery_timeout: Optional[int] = Field(None, ge=1, description="熔断恢复等待时间（秒，≥1）")
    fallback_channel: Optional[str] = Field(None, max_length=64, description="备用渠道名称")


class SmsPolicyOut(BaseModel):
    name: str
    code_ttl: int
    rate_limit_phone_per_minute: int
    rate_limit_phone_per_day: int
    rate_limit_ip_per_minute: int
    rate_limit_ip_per_day: int
    records_retention_days: int
    failure_threshold: int
    recovery_timeout: int
    fallback_channel: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SmsPolicyListResponse(BaseModel):
    total: int
    items: List[SmsPolicyOut]


# ---------------------------------------------------------------------------
# Admin – SMS Channel CRUD schemas
# ---------------------------------------------------------------------------


class SmsChannelCreate(BaseModel):
    """创建或完整替换渠道配置。"""
    provider: str = Field(..., max_length=32, description="供应商标识（aliyun / aliyun_phone_svc / tencent / chuanglan）")
    is_default: bool = Field(False, description="是否为默认渠道")
    policy_name: Optional[str] = Field(None, max_length=64, description="关联策略名称；留空时使用 default 策略")
    # Aliyun / AliyunPhoneSvc credentials
    access_key_id: Optional[str] = Field(None, description="Access Key ID")
    access_key_secret: Optional[str] = Field(None, description="Access Key Secret")
    sign_name: Optional[str] = Field(None, description="短信签名")
    endpoint: Optional[str] = Field(None, description="API Endpoint（留空使用默认值）")
    # ChuangLan credentials
    account: Optional[str] = Field(None, description="账号（创蓝云）")
    password: Optional[str] = Field(None, description="密码（创蓝云）")
    api_url: Optional[str] = Field(None, description="API 地址（创蓝云）")
    # Tencent credentials
    app_id: Optional[str] = Field(None, description="SdkAppId（腾讯云）")
    secret_id: Optional[str] = Field(None, description="SecretId（腾讯云）")
    secret_key: Optional[str] = Field(None, description="SecretKey（腾讯云）")


class SmsChannelUpdate(BaseModel):
    """局部更新渠道——仅更新提交的字段。"""
    provider: Optional[str] = Field(None, max_length=32, description="供应商标识")
    is_default: Optional[bool] = Field(None, description="是否为默认渠道")
    policy_name: Optional[str] = Field(None, max_length=64, description="关联策略名称")
    access_key_id: Optional[str] = Field(None, description="Access Key ID")
    access_key_secret: Optional[str] = Field(None, description="Access Key Secret")
    sign_name: Optional[str] = Field(None, description="短信签名")
    endpoint: Optional[str] = Field(None, description="API Endpoint")
    account: Optional[str] = Field(None, description="账号（创蓝云）")
    password: Optional[str] = Field(None, description="密码（创蓝云）")
    api_url: Optional[str] = Field(None, description="API 地址（创蓝云）")
    app_id: Optional[str] = Field(None, description="SdkAppId（腾讯云）")
    secret_id: Optional[str] = Field(None, description="SecretId（腾讯云）")
    secret_key: Optional[str] = Field(None, description="SecretKey（腾讯云）")


class SmsChannelOut(BaseModel):
    """渠道配置（敏感字段已脱敏）。"""
    name: str
    is_default: bool = False
    provider: str
    policy_name: Optional[str] = None
    # Aliyun / AliyunPhoneSvc
    access_key_id: Optional[str] = None
    access_key_secret: Optional[str] = None  # always "***" when set
    sign_name: Optional[str] = None
    endpoint: Optional[str] = None
    # ChuangLan
    account: Optional[str] = None
    password: Optional[str] = None  # always "***" when set
    api_url: Optional[str] = None
    # Tencent
    app_id: Optional[str] = None
    secret_id: Optional[str] = None
    secret_key: Optional[str] = None  # always "***" when set
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SmsChannelListResponse(BaseModel):
    total: int
    items: List[SmsChannelOut]


# ---------------------------------------------------------------------------
# Admin – SMS Client Key CRUD schemas
# ---------------------------------------------------------------------------


class SmsClientKeyCreate(BaseModel):
    api_key: str = Field(..., max_length=128, description="客户端 API Key（X-API-Key 头）")
    channel: str = Field(..., max_length=64, description="映射到的渠道名称")


class SmsClientKeyOut(BaseModel):
    api_key: str
    channel: str


class SmsClientKeyListResponse(BaseModel):
    total: int
    items: List[SmsClientKeyOut]

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
    channel: Optional[str] = Field(None, max_length=64, description="Named channel for multi-credential routing (e.g. 'external', 'internal')")


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
# Admin – Provider credential schemas (for PUT /api/sms/config)
# ---------------------------------------------------------------------------


class ChuanglanCredentialsUpdate(BaseModel):
    account: Optional[str] = Field(None, description="账号")
    password: Optional[str] = Field(None, description="密码")
    api_url: Optional[str] = Field(None, description="API 地址")


class AliyunCredentialsUpdate(BaseModel):
    access_key_id: Optional[str] = Field(None, description="Access Key ID")
    access_key_secret: Optional[str] = Field(None, description="Access Key Secret")
    sign_name: Optional[str] = Field(None, description="短信签名")
    endpoint: Optional[str] = Field(None, description="API Endpoint")


class TencentCredentialsUpdate(BaseModel):
    secret_id: Optional[str] = Field(None, description="SecretId")
    secret_key: Optional[str] = Field(None, description="SecretKey")
    app_id: Optional[str] = Field(None, description="SdkAppId")
    sign_name: Optional[str] = Field(None, description="短信签名")


# ---------------------------------------------------------------------------
# Admin – SMS Configuration schemas
# ---------------------------------------------------------------------------


class SmsChannelConfig(BaseModel):
    """Single named channel configuration (provider + credentials)."""
    provider: str = Field(..., description="供应商标识（aliyun / aliyun_phone_svc / tencent / chuanglan）")
    access_key_id: Optional[str] = Field(None, description="Access Key ID")
    access_key_secret: Optional[str] = Field(None, description="Access Key Secret（写入时有效，读取时脱敏）")
    sign_name: Optional[str] = Field(None, description="短信签名")
    endpoint: Optional[str] = Field(None, description="API Endpoint（留空使用默认值）")


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
    sms_channels: Dict[str, dict] = Field(default_factory=dict, description="渠道配置（access_key_secret 已脱敏）")
    sms_client_keys: Dict[str, str] = Field(default_factory=dict, description="客户端 API Key → 渠道名称映射")
    # Provider credentials (secrets masked to "***")
    chuanglan: dict = Field(default_factory=dict, description="创蓝云凭据（password 已脱敏）")
    aliyun: dict = Field(default_factory=dict, description="阿里云短信凭据（access_key_secret 已脱敏）")
    aliyun_phone_svc: dict = Field(default_factory=dict, description="阿里云号码认证凭据（access_key_secret 已脱敏）")
    tencent: dict = Field(default_factory=dict, description="腾讯云凭据（secret_key 已脱敏）")


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
    sms_channels: Optional[Dict[str, Optional[SmsChannelConfig]]] = Field(
        None, description="渠道配置增量更新，值为 null 则删除该渠道"
    )
    sms_client_keys: Optional[Dict[str, Optional[str]]] = Field(
        None, description="客户端 API Key 增量更新，值为 null 则删除该 Key"
    )
    # Provider credentials – partial update: only supplied fields are changed
    chuanglan: Optional[ChuanglanCredentialsUpdate] = Field(None, description="创蓝云凭据（部分更新）")
    aliyun: Optional[AliyunCredentialsUpdate] = Field(None, description="阿里云短信凭据（部分更新）")
    aliyun_phone_svc: Optional[AliyunCredentialsUpdate] = Field(None, description="阿里云号码认证凭据（部分更新）")
    tencent: Optional[TencentCredentialsUpdate] = Field(None, description="腾讯云凭据（部分更新）")


# ---------------------------------------------------------------------------
# Admin – SMS Channel CRUD schemas
# ---------------------------------------------------------------------------


class SmsChannelCreate(BaseModel):
    """Create or replace a named channel configuration."""
    provider: str = Field(..., max_length=32, description="供应商标识（aliyun / aliyun_phone_svc / tencent / chuanglan）")
    access_key_id: Optional[str] = Field(None, description="Access Key ID")
    access_key_secret: Optional[str] = Field(None, description="Access Key Secret")
    sign_name: Optional[str] = Field(None, description="短信签名")
    endpoint: Optional[str] = Field(None, description="API Endpoint（留空使用默认值）")
    account: Optional[str] = Field(None, description="账号（创蓝云）")
    password: Optional[str] = Field(None, description="密码（创蓝云）")
    api_url: Optional[str] = Field(None, description="API 地址（创蓝云）")
    app_id: Optional[str] = Field(None, description="SdkAppId（腾讯云）")
    secret_id: Optional[str] = Field(None, description="SecretId（腾讯云）")
    secret_key: Optional[str] = Field(None, description="SecretKey（腾讯云）")


class SmsChannelUpdate(BaseModel):
    """Partial update for a named channel — only supplied fields are changed."""
    provider: Optional[str] = Field(None, max_length=32, description="供应商标识")
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
    """Channel config returned to the client — secrets masked."""
    name: str
    provider: str
    access_key_id: Optional[str] = None
    access_key_secret: Optional[str] = None  # always "***" when set
    sign_name: Optional[str] = None
    endpoint: Optional[str] = None
    account: Optional[str] = None
    password: Optional[str] = None  # always "***" when set
    api_url: Optional[str] = None
    app_id: Optional[str] = None
    secret_id: Optional[str] = None
    secret_key: Optional[str] = None  # always "***" when set


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

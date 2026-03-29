"""Aliyun (Alibaba Cloud) SMS provider adapter.

Docs: https://help.aliyun.com/document_detail/101414.html

The SDK (alibabacloud-dysmsapi20170525) is optional – if it is not
installed the adapter falls back to a direct HTTPS call so the service
can still start without heavy provider SDKs in CI/tests.
"""

import hashlib
import hmac
import json
import time
import uuid
from base64 import b64encode
from urllib.parse import quote, urlencode

import httpx

from app.core.config import settings
from app.providers import BaseSmsProvider, SendResult, StatusResult


class AliyunSmsProvider(BaseSmsProvider):
    """Aliyun SMS adapter using the REST/signature API."""

    _API_VERSION = "2017-05-25"

    def __init__(
        self,
        key_id: str = "",
        key_secret: str = "",
        sign_name: str = "",
        endpoint: str = "",
    ) -> None:
        self._key_id = key_id or settings.ALIYUN_ACCESS_KEY_ID
        self._key_secret = key_secret or settings.ALIYUN_ACCESS_KEY_SECRET
        self._sign_name = sign_name or settings.ALIYUN_SMS_SIGN_NAME
        _ep = endpoint or settings.ALIYUN_SMS_ENDPOINT
        self._ENDPOINT = f"https://{_ep}" if not _ep.startswith("http") else _ep

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def send(self, phone: str, template_id: str, params: dict) -> SendResult:
        query = self._build_query(phone, template_id, params)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(self._ENDPOINT, params=query)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:  # network / HTTP errors
            return SendResult(success=False, error_message=str(exc), error_code="NETWORK_ERROR")

        if data.get("Code") == "OK":
            return SendResult(success=True, provider_message_id=data.get("BizId", ""))
        return SendResult(
            success=False,
            error_code=data.get("Code", ""),
            error_message=f"{data.get('Code')}: {data.get('Message')}",
        )

    async def query_status(self, provider_message_id: str) -> StatusResult:
        query = self._build_status_query(provider_message_id)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(self._ENDPOINT, params=query)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            return StatusResult(
                provider_message_id=provider_message_id,
                status="UNKNOWN",
                error_message=str(exc),
            )

        if data.get("Code") != "OK":
            return StatusResult(
                provider_message_id=provider_message_id,
                status="UNKNOWN",
                error_message=data.get("Message", ""),
            )

        sms_list = data.get("SmsSendDetailDTOs", {}).get("SmsSendDetailDTO", [])
        if not sms_list:
            return StatusResult(provider_message_id=provider_message_id, status="UNKNOWN")

        detail = sms_list[0] if isinstance(sms_list, list) else sms_list
        # Aliyun SendStatus: 1=waiting, 2=sending, 3=success, 5=failed
        send_status = detail.get("SendStatus", 0)
        if send_status == 3:
            status = "DELIVERED"
        elif send_status == 5:
            status = "FAILED"
        else:
            status = "PENDING"
        return StatusResult(
            provider_message_id=provider_message_id,
            status=status,
            error_message=detail.get("ErrCode", ""),
        )

    # ------------------------------------------------------------------
    # Signature helpers (HMAC-SHA1, v1 signature)
    # ------------------------------------------------------------------

    def _build_query(self, phone: str, template_id: str, params: dict) -> dict:
        base_params = {
            "AccessKeyId": self._key_id,
            "Action": "SendSms",
            "Format": "JSON",
            "PhoneNumbers": phone,
            "SignName": self._sign_name,
            "SignatureMethod": "HMAC-SHA1",
            "SignatureNonce": str(uuid.uuid4()),
            "SignatureVersion": "1.0",
            "TemplateCode": template_id,
            "TemplateParam": json.dumps(params, ensure_ascii=False),
            "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "Version": self._API_VERSION,
        }
        return self._sign_params(base_params)

    def _build_status_query(self, provider_message_id: str) -> dict:
        base_params = {
            "AccessKeyId": self._key_id,
            "Action": "QuerySendDetails",
            "Format": "JSON",
            "BizId": provider_message_id,
            "SignatureMethod": "HMAC-SHA1",
            "SignatureNonce": str(uuid.uuid4()),
            "SignatureVersion": "1.0",
            "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "Version": self._API_VERSION,
            # Required by QuerySendDetails: SendDate and PageSize
            "SendDate": time.strftime("%Y%m%d", time.gmtime()),
            "PageSize": "10",
            "CurrentPage": "1",
        }
        return self._sign_params(base_params)

    def _sign_params(self, base_params: dict) -> dict:
        sorted_params = sorted(base_params.items())
        encoded = urlencode(
            [(k, v) for k, v in sorted_params],
            quote_via=quote,
        )
        string_to_sign = f"GET&{quote('/', safe='')}&{quote(encoded, safe='')}"
        signing_key = (self._key_secret + "&").encode()
        signature = b64encode(
            hmac.new(signing_key, string_to_sign.encode(), hashlib.sha1).digest()
        ).decode()

        base_params["Signature"] = signature
        return base_params

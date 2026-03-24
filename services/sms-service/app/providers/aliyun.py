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
from app.providers import BaseSmsProvider, SendResult


class AliyunSmsProvider(BaseSmsProvider):
    """Aliyun SMS adapter using the REST/signature API."""

    _ENDPOINT = "https://dysmsapi.aliyuncs.com"
    _API_VERSION = "2017-05-25"

    def __init__(self) -> None:
        self._key_id = settings.ALIYUN_ACCESS_KEY_ID
        self._key_secret = settings.ALIYUN_ACCESS_KEY_SECRET
        self._sign_name = settings.ALIYUN_SMS_SIGN_NAME

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
            return SendResult(success=False, error_message=str(exc))

        if data.get("Code") == "OK":
            return SendResult(success=True, provider_message_id=data.get("BizId", ""))
        return SendResult(
            success=False,
            error_message=f"{data.get('Code')}: {data.get('Message')}",
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

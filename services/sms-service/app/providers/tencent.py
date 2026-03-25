"""Tencent Cloud SMS provider adapter.

Docs: https://cloud.tencent.com/document/product/382/55981
"""

import hashlib
import hmac
import json
import time

import httpx

from app.core.config import settings
from app.providers import BaseSmsProvider, SendResult, StatusResult


class TencentSmsProvider(BaseSmsProvider):
    """Tencent Cloud SMS adapter using TC3-HMAC-SHA256 signature."""

    _HOST = "sms.tencentcloudapi.com"
    _ENDPOINT = f"https://{_HOST}"
    _SERVICE = "sms"
    _VERSION = "2021-01-11"
    _ACTION = "SendSms"

    def __init__(self) -> None:
        self._secret_id = settings.TENCENT_SECRET_ID
        self._secret_key = settings.TENCENT_SECRET_KEY
        self._app_id = settings.TENCENT_SMS_APP_ID
        self._sign_name = settings.TENCENT_SMS_SIGN_NAME

    async def send(self, phone: str, template_id: str, params: dict) -> SendResult:
        payload = {
            "SmsSdkAppId": self._app_id,
            "SignName": self._sign_name,
            "TemplateId": template_id,
            "TemplateParamSet": list(params.values()),
            "PhoneNumberSet": [phone],
        }
        headers = self._build_headers(payload, action=self._ACTION)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    self._ENDPOINT,
                    content=json.dumps(payload),
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            return SendResult(success=False, error_message=str(exc), error_code="NETWORK_ERROR")

        send_status_set = data.get("Response", {}).get("SendStatusSet") or []
        if send_status_set and send_status_set[0].get("Code") == "Ok":
            return SendResult(
                success=True,
                provider_message_id=send_status_set[0].get("SerialNo", ""),
            )
        first = send_status_set[0] if send_status_set else {}
        return SendResult(
            success=False,
            error_code=first.get("Code", ""),
            error_message=first.get("Message", "unknown"),
        )

    async def query_status(self, provider_message_id: str) -> StatusResult:
        payload = {
            "SmsSdkAppId": self._app_id,
            "Limit": 10,
            "BeginTime": int(time.time()) - 86400,
            "EndTime": int(time.time()),
            "PhoneNumber": "",
        }
        headers = self._build_headers(payload, action="PullSmsSendStatus")
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    self._ENDPOINT,
                    content=json.dumps(payload),
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            return StatusResult(
                provider_message_id=provider_message_id,
                status="UNKNOWN",
                error_message=str(exc),
            )

        response = data.get("Response", {})
        if "Error" in response:
            return StatusResult(
                provider_message_id=provider_message_id,
                status="UNKNOWN",
                error_message=response["Error"].get("Message", ""),
            )

        pull_list = response.get("PullSmsSendStatusSet") or []
        for item in pull_list:
            if item.get("SerialNo") == provider_message_id:
                receipt_status = item.get("ReportStatus", "")
                if receipt_status == "SUCCESS":
                    status = "DELIVERED"
                elif receipt_status:
                    status = "FAILED"
                else:
                    status = "PENDING"
                return StatusResult(
                    provider_message_id=provider_message_id,
                    status=status,
                    error_message=item.get("Description", ""),
                )

        return StatusResult(provider_message_id=provider_message_id, status="PENDING")

    # ------------------------------------------------------------------
    # TC3-HMAC-SHA256 helpers
    # ------------------------------------------------------------------

    def _sign(self, key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode(), hashlib.sha256).digest()

    def _build_headers(self, payload: dict, action: str) -> dict:
        body = json.dumps(payload)
        timestamp = int(time.time())
        date = time.strftime("%Y-%m-%d", time.gmtime(timestamp))

        canonical_request = "\n".join(
            [
                "POST",
                "/",
                "",
                "content-type:application/json\nhost:" + self._HOST + "\n",
                "content-type;host",
                hashlib.sha256(body.encode()).hexdigest(),
            ]
        )
        credential_scope = f"{date}/{self._SERVICE}/tc3_request"
        string_to_sign = "\n".join(
            [
                "TC3-HMAC-SHA256",
                str(timestamp),
                credential_scope,
                hashlib.sha256(canonical_request.encode()).hexdigest(),
            ]
        )

        secret_date = self._sign(f"TC3{self._secret_key}".encode(), date)
        secret_service = self._sign(secret_date, self._SERVICE)
        secret_signing = self._sign(secret_service, "tc3_request")
        signature = hmac.new(
            secret_signing, string_to_sign.encode(), hashlib.sha256
        ).hexdigest()

        authorization = (
            f"TC3-HMAC-SHA256 Credential={self._secret_id}/{credential_scope}, "
            f"SignedHeaders=content-type;host, Signature={signature}"
        )
        return {
            "Authorization": authorization,
            "Content-Type": "application/json",
            "Host": self._HOST,
            "X-TC-Action": action,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": self._VERSION,
        }

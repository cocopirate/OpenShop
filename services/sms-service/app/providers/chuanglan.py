"""ChuangLan (创蓝云) SMS provider adapter.

API docs: https://zz.253.com/v5/document
"""
import json

import httpx

from app.core.config import settings
from app.providers import BaseSmsProvider, SendResult, StatusResult


class ChuangLanSmsProvider(BaseSmsProvider):
    """ChuangLan SMS adapter."""

    def __init__(self) -> None:
        self._account = settings.CHUANGLAN_ACCOUNT
        self._password = settings.CHUANGLAN_PASSWORD
        self._send_url = settings.CHUANGLAN_API_URL
        self._query_url = "https://smssh1.253.com/msg/v1/report/json"

    async def send(self, phone: str, template_id: str, params: dict) -> SendResult:
        content = self._build_content(template_id, params)
        payload = {
            "account": self._account,
            "password": self._password,
            "phone": phone,
            "msg": content,
            "report": "true",
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    self._send_url,
                    content=json.dumps(payload),
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            return SendResult(success=False, error_message=str(exc), error_code="NETWORK_ERROR")

        code = str(data.get("code", ""))
        if code == "0":
            return SendResult(
                success=True,
                provider_message_id=data.get("msgId", ""),
            )
        return SendResult(
            success=False,
            error_code=code,
            error_message=data.get("errorMsg", f"ChuangLan error code: {code}"),
        )

    async def query_status(self, provider_message_id: str) -> StatusResult:
        payload = {
            "account": self._account,
            "password": self._password,
            "msgId": provider_message_id,
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    self._query_url,
                    content=json.dumps(payload),
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            return StatusResult(
                provider_message_id=provider_message_id,
                status="UNKNOWN",
                error_message=str(exc),
            )

        code = str(data.get("code", ""))
        if code != "0":
            return StatusResult(
                provider_message_id=provider_message_id,
                status="UNKNOWN",
                error_message=data.get("errorMsg", ""),
            )

        # ChuangLan report code: "DELIVRD"=success, others=error, empty=pending
        report_code = str(data.get("reportCode", ""))
        if report_code == "DELIVRD":
            status = "DELIVERED"
        elif report_code:
            status = "FAILED"
        else:
            status = "PENDING"
        return StatusResult(provider_message_id=provider_message_id, status=status)

    @staticmethod
    def _build_content(template_id: str, params: dict) -> str:
        """Build SMS text. If params contain 'content' key, use it directly."""
        if "content" in params:
            return params["content"]
        parts = [str(v) for v in params.values()]
        return " ".join(parts) if parts else template_id

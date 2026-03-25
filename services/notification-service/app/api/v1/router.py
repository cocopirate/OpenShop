from enum import Enum
from typing import Optional
import uuid

import httpx
import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()
log = structlog.get_logger(__name__)

_sms_client: Optional[httpx.AsyncClient] = None


def set_sms_client(client: httpx.AsyncClient) -> None:
    """Inject the shared httpx client (called from app lifespan)."""
    global _sms_client
    _sms_client = client


def _get_sms_client() -> httpx.AsyncClient:
    if _sms_client is not None:
        return _sms_client
    # Fallback: create a one-off client (e.g. during tests)
    return httpx.AsyncClient(timeout=10)


class NotificationChannel(str, Enum):
    push = "push"
    email = "email"
    in_app = "in_app"
    sms = "sms"


class SendRequest(BaseModel):
    user_id: str
    channel: NotificationChannel
    title: str
    content: str
    template_id: Optional[str] = None
    # SMS-specific fields (required when channel == "sms")
    phone: Optional[str] = None
    sms_params: Optional[dict] = None
    request_id: Optional[str] = None


@router.post("/notifications/send", summary="发送通知")
async def send_notification(req: SendRequest):
    """发送通知。当 channel=sms 时，调用 sms-service 发送短信。"""
    if req.channel == NotificationChannel.sms:
        if not req.phone:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="phone is required when channel is sms",
            )
        if not req.template_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="template_id is required when channel is sms",
            )
        payload = {
            "phone": req.phone,
            "template_id": req.template_id,
            "params": req.sms_params or {},
        }
        if req.request_id:
            payload["request_id"] = req.request_id

        try:
            client = _get_sms_client()
            resp = await client.post(
                f"{settings.SMS_SERVICE_URL}/api/v1/sms/send",
                json=payload,
            )
            resp.raise_for_status()
            sms_data = resp.json()
        except httpx.HTTPStatusError as exc:
            log.error(
                "notification.sms.http_error",
                user_id=req.user_id,
                status_code=exc.response.status_code,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="sms-service returned an error",
            ) from exc
        except Exception as exc:
            log.error("notification.sms.network_error", user_id=req.user_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="failed to reach sms-service",
            ) from exc

        return {
            "notification_id": sms_data.get("message_id") or str(uuid.uuid4()),
            "channel": "sms",
            "status": sms_data.get("status", "sent"),
            "provider": sms_data.get("provider"),
        }

    # push / email / in_app channels – queued for async processing
    return {"notification_id": "NOTIF-001", "channel": req.channel, "status": "queued"}


@router.get("/notifications/{user_id}/inbox", summary="获取用户站内信")
async def get_inbox(user_id: str, page: int = 1, size: int = 20):
    return {"user_id": user_id, "items": [], "total": 0}


@router.put("/notifications/{notification_id}/read", summary="标记已读")
async def mark_read(notification_id: str):
    return {"notification_id": notification_id, "read": True}


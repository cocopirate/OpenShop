from enum import Enum

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class NotificationChannel(str, Enum):
    push = "push"
    email = "email"
    in_app = "in_app"


class SendRequest(BaseModel):
    user_id: str
    channel: NotificationChannel
    title: str
    content: str
    template_id: Optional[str] = None


@router.post("/notifications/send", summary="发送通知")
async def send_notification(req: SendRequest):
    return {"notification_id": "NOTIF-001", "status": "queued"}


@router.get("/notifications/{user_id}/inbox", summary="获取用户站内信")
async def get_inbox(user_id: str, page: int = 1, size: int = 20):
    return {"user_id": user_id, "items": [], "total": 0}


@router.put("/notifications/{notification_id}/read", summary="标记已读")
async def mark_read(notification_id: str):
    return {"notification_id": notification_id, "read": True}

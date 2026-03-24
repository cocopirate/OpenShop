from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class SmsSendRequest(BaseModel):
    phone: str
    template_id: str
    params: dict


class SmsVerifyRequest(BaseModel):
    phone: str
    code: str


@router.post("/sms/send", summary="发送短信")
async def send_sms(req: SmsSendRequest):
    return {"message_id": "SMS-001", "status": "sent"}


@router.get("/sms/records/{phone}", summary="查询发送记录")
async def get_sms_records(phone: str):
    return {"phone": phone, "records": []}


@router.post("/sms/verify", summary="验证短信验证码")
async def verify_sms(req: SmsVerifyRequest):
    return {"phone": req.phone, "valid": True}

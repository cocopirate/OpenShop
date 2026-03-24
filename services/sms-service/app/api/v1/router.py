from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.sms import (
    SmsSendRequest,
    SmsSendResponse,
    SmsRecordOut,
    SmsVerifyRequest,
    SmsVerifyResponse,
)
from app.services.sms_service import (
    get_sms_records,
    send_sms,
    send_verification_code,
    verify_code,
)

router = APIRouter()


@router.post(
    "/sms/send",
    response_model=SmsSendResponse,
    status_code=status.HTTP_201_CREATED,
    summary="发送短信",
)
async def send_sms_endpoint(
    req: SmsSendRequest, db: AsyncSession = Depends(get_db)
):
    record = await send_sms(db, req.phone, req.template_id, req.params)
    return SmsSendResponse(
        message_id=str(record.id),
        status=record.status,
        provider=record.provider,
    )


@router.post(
    "/sms/send-code",
    status_code=status.HTTP_201_CREATED,
    summary="发送验证码短信",
)
async def send_code_endpoint(
    phone: str,
    template_id: str,
    db: AsyncSession = Depends(get_db),
):
    await send_verification_code(db, phone, template_id)
    return {"message": "verification code sent"}


@router.get(
    "/sms/records/{phone}",
    response_model=list[SmsRecordOut],
    summary="查询发送记录",
)
async def get_sms_records_endpoint(
    phone: str,
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    records = await get_sms_records(db, phone, page=page, size=size)
    return records


@router.post(
    "/sms/verify",
    response_model=SmsVerifyResponse,
    summary="验证短信验证码",
)
async def verify_sms(req: SmsVerifyRequest):
    valid = await verify_code(req.phone, req.code)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid or expired verification code",
        )
    return SmsVerifyResponse(phone=req.phone, valid=True)



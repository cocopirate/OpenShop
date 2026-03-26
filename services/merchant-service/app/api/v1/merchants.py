from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.response import ok, err, MERCHANT_NOT_FOUND
from app.schemas.merchant import MerchantCreate, MerchantUpdate, MerchantStatusUpdate, MerchantResponse
from app.services import merchant_service

router = APIRouter()


@router.post("", status_code=201)
async def create_merchant(body: MerchantCreate, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    merchant = await merchant_service.create_merchant(db, body)
    return JSONResponse(status_code=201, content=ok(MerchantResponse.model_validate(merchant).model_dump(mode="json")))


@router.get("/{merchant_id}")
async def get_merchant(merchant_id: int, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    merchant = await merchant_service.get_merchant(db, merchant_id)
    if not merchant:
        return JSONResponse(status_code=404, content=err(MERCHANT_NOT_FOUND, "Merchant not found"))
    return JSONResponse(content=ok(MerchantResponse.model_validate(merchant).model_dump(mode="json")))


@router.put("/{merchant_id}")
async def update_merchant(merchant_id: int, body: MerchantUpdate, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    merchant = await merchant_service.update_merchant(db, merchant_id, body)
    if not merchant:
        return JSONResponse(status_code=404, content=err(MERCHANT_NOT_FOUND, "Merchant not found"))
    return JSONResponse(content=ok(MerchantResponse.model_validate(merchant).model_dump(mode="json")))


@router.post("/{merchant_id}/status")
async def update_merchant_status(merchant_id: int, body: MerchantStatusUpdate, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    merchant = await merchant_service.update_merchant_status(db, merchant_id, body.status)
    if not merchant:
        return JSONResponse(status_code=404, content=err(MERCHANT_NOT_FOUND, "Merchant not found"))
    return JSONResponse(content=ok(MerchantResponse.model_validate(merchant).model_dump(mode="json")))

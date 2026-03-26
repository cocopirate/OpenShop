from __future__ import annotations
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.response import ok, err, SUB_ACCOUNT_NOT_FOUND
from app.schemas.sub_account import SubAccountCreate, SubAccountUpdate, SubAccountResponse, RoleAssignRequest
from app.services import sub_account_service

router = APIRouter()


@router.get("/{merchant_id}/sub-accounts")
async def list_sub_accounts(merchant_id: int, page: int = 1, page_size: int = 20, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    items, total = await sub_account_service.list_sub_accounts(db, merchant_id, page, page_size)
    return JSONResponse(content=ok({"items": [SubAccountResponse.model_validate(s).model_dump(mode="json") for s in items], "total": total}))


@router.post("/{merchant_id}/sub-accounts", status_code=201)
async def create_sub_account(merchant_id: int, body: SubAccountCreate, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    sub = await sub_account_service.create_sub_account(db, merchant_id, body)
    return JSONResponse(status_code=201, content=ok(SubAccountResponse.model_validate(sub).model_dump(mode="json")))


@router.put("/{merchant_id}/sub-accounts/{sub_id}")
async def update_sub_account(merchant_id: int, sub_id: int, body: SubAccountUpdate, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    sub = await sub_account_service.update_sub_account(db, sub_id, body)
    if not sub:
        return JSONResponse(status_code=404, content=err(SUB_ACCOUNT_NOT_FOUND, "Sub-account not found"))
    return JSONResponse(content=ok(SubAccountResponse.model_validate(sub).model_dump(mode="json")))


@router.delete("/{merchant_id}/sub-accounts/{sub_id}", status_code=204)
async def delete_sub_account(merchant_id: int, sub_id: int, db: AsyncSession = Depends(get_db)):
    await sub_account_service.delete_sub_account(db, sub_id)


@router.post("/{merchant_id}/sub-accounts/{sub_id}/roles")
async def assign_roles(merchant_id: int, sub_id: int, body: RoleAssignRequest, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    await sub_account_service.assign_roles(db, sub_id, body.role_ids)
    return JSONResponse(content=ok({"message": "roles assigned"}))

from __future__ import annotations
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.response import ok, err, STORE_NOT_FOUND
from app.schemas.store import StoreCreate, StoreUpdate, StoreResponse
from app.services import store_service

router = APIRouter()


@router.get("/{merchant_id}/stores")
async def list_stores(merchant_id: int, page: int = 1, page_size: int = 20, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    items, total = await store_service.list_stores(db, merchant_id, page, page_size)
    return JSONResponse(content=ok({"items": [StoreResponse.model_validate(s).model_dump(mode="json") for s in items], "total": total}))


@router.post("/{merchant_id}/stores", status_code=201)
async def create_store(merchant_id: int, body: StoreCreate, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    store = await store_service.create_store(db, merchant_id, body)
    return JSONResponse(status_code=201, content=ok(StoreResponse.model_validate(store).model_dump(mode="json")))


@router.put("/{merchant_id}/stores/{store_id}")
async def update_store(merchant_id: int, store_id: int, body: StoreUpdate, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    store = await store_service.update_store(db, store_id, body)
    if not store:
        return JSONResponse(status_code=404, content=err(STORE_NOT_FOUND, "Store not found"))
    return JSONResponse(content=ok(StoreResponse.model_validate(store).model_dump(mode="json")))


@router.delete("/{merchant_id}/stores/{store_id}", status_code=204)
async def delete_store(merchant_id: int, store_id: int, db: AsyncSession = Depends(get_db)):
    await store_service.delete_store(db, store_id)

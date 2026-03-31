"""Admin API routes for SKU management."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import err, ok, SKU_NOT_FOUND
from app.schemas.sku import SkuBatchCreate, SkuResponse, SkuUpdate
from app.services import sku_service

router = APIRouter()


@router.post("/batch", status_code=201, summary="批量创建SKU")
async def batch_create_skus(body: SkuBatchCreate, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    skus = await sku_service.batch_create_skus(db, body.items)
    return JSONResponse(
        status_code=201,
        content=ok([SkuResponse.model_validate(s).model_dump(mode="json") for s in skus]),
    )


@router.put("/{sku_id}", summary="编辑SKU")
async def update_sku(sku_id: int, body: SkuUpdate, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    sku = await sku_service.update_sku(db, sku_id, body)
    if not sku:
        return JSONResponse(status_code=404, content=err(SKU_NOT_FOUND, "SKU not found"))
    return JSONResponse(content=ok(SkuResponse.model_validate(sku).model_dump(mode="json")))


@router.delete("/{sku_id}", summary="删除SKU")
async def delete_sku(sku_id: int, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    deleted = await sku_service.delete_sku(db, sku_id)
    if not deleted:
        return JSONResponse(status_code=404, content=err(SKU_NOT_FOUND, "SKU not found"))
    return JSONResponse(content=ok(None, "deleted"))

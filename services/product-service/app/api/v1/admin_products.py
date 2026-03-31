"""Admin API routes for SPU (product) management."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import err, ok, SPU_NOT_FOUND
from app.models.spu import SpuStatus
from app.schemas.spu import SpuCreate, SpuListResponse, SpuResponse, SpuUpdate
from app.services import spu_service

router = APIRouter()


@router.post("", status_code=201, summary="创建商品(SPU)")
async def create_product(
    body: SpuCreate, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    spu = await spu_service.create_spu(db, body)
    return JSONResponse(
        status_code=201,
        content=ok(SpuResponse.model_validate(spu).model_dump(mode="json")),
    )


@router.get("", summary="商品列表(Admin)")
async def list_products(
    category_id: Optional[int] = Query(None),
    status: Optional[SpuStatus] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    items, total = await spu_service.list_spus(db, category_id=category_id, status=status, page=page, size=size)
    data = SpuListResponse(
        items=[SpuResponse.model_validate(s) for s in items],
        total=total,
        page=page,
        size=size,
    )
    return JSONResponse(content=ok(data.model_dump(mode="json")))


@router.get("/{product_id}", summary="商品详情(Admin)")
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    spu = await spu_service.get_spu(db, product_id)
    if not spu:
        return JSONResponse(status_code=404, content=err(SPU_NOT_FOUND, "Product not found"))
    return JSONResponse(content=ok(SpuResponse.model_validate(spu).model_dump(mode="json")))


@router.put("/{product_id}", summary="编辑商品(SPU)")
async def update_product(
    product_id: int, body: SpuUpdate, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    spu = await spu_service.update_spu(db, product_id, body)
    if not spu:
        return JSONResponse(status_code=404, content=err(SPU_NOT_FOUND, "Product not found"))
    return JSONResponse(content=ok(SpuResponse.model_validate(spu).model_dump(mode="json")))


@router.post("/{product_id}/publish", summary="商品上架")
async def publish_product(product_id: int, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    spu = await spu_service.publish_spu(db, product_id)
    if not spu:
        return JSONResponse(status_code=404, content=err(SPU_NOT_FOUND, "Product not found"))
    return JSONResponse(content=ok(SpuResponse.model_validate(spu).model_dump(mode="json")))


@router.post("/{product_id}/unpublish", summary="商品下架")
async def unpublish_product(product_id: int, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    spu = await spu_service.unpublish_spu(db, product_id)
    if not spu:
        return JSONResponse(status_code=404, content=err(SPU_NOT_FOUND, "Product not found"))
    return JSONResponse(content=ok(SpuResponse.model_validate(spu).model_dump(mode="json")))

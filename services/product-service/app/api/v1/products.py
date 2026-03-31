"""Public API routes for product queries (App/BFF use)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import SPU_NOT_FOUND, err, ok
from app.models.spu import SpuStatus
from app.schemas.spu import SpuListResponse, SpuResponse
from app.services import spu_service

router = APIRouter()


@router.get("", tags=["public"], summary="商品列表(公开)")
async def list_products(
    category_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    items, total = await spu_service.list_online_spus(db, category_id=category_id, page=page, size=size)
    data = SpuListResponse(
        items=[SpuResponse.model_validate(s) for s in items],
        total=total,
        page=page,
        size=size,
    )
    return JSONResponse(content=ok(data.model_dump(mode="json")))


@router.get("/{spu_id}", tags=["public"], summary="商品详情(公开)")
async def get_product(spu_id: int, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    spu = await spu_service.get_spu(db, spu_id)
    if not spu or spu.status != SpuStatus.ONLINE:
        return JSONResponse(status_code=404, content=err(SPU_NOT_FOUND, "Product not found"))
    return JSONResponse(content=ok(SpuResponse.model_validate(spu).model_dump(mode="json")))

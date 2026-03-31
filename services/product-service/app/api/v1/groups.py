"""Public API routes for product group queries (App/BFF use)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import GROUP_NOT_FOUND, err, ok
from app.schemas.spu import SpuResponse
from app.services import product_group_service

router = APIRouter()


@router.get("/{group_id}/products", tags=["public"], summary="分组商品列表(公开)")
async def list_group_products(group_id: int, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    group = await product_group_service.get_group(db, group_id)
    if not group:
        return JSONResponse(status_code=404, content=err(GROUP_NOT_FOUND, "Group not found"))
    spus = await product_group_service.list_group_spus(db, group_id)
    return JSONResponse(
        content=ok([SpuResponse.model_validate(s).model_dump(mode="json") for s in spus])
    )

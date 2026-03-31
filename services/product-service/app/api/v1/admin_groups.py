"""Admin API routes for ProductGroup management."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import DUPLICATE_GROUP_PRODUCT, GROUP_NOT_FOUND, SPU_NOT_FOUND, err, ok
from app.schemas.product_group import (
    GroupItemCreate,
    GroupItemResponse,
    ProductGroupCreate,
    ProductGroupResponse,
    ProductGroupUpdate,
)
from app.schemas.spu import SpuResponse
from app.services import product_group_service, spu_service

router = APIRouter()


@router.post("", status_code=201, summary="创建商品分组")
async def create_group(body: ProductGroupCreate, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    group = await product_group_service.create_group(db, body)
    return JSONResponse(
        status_code=201,
        content=ok(ProductGroupResponse.model_validate(group).model_dump(mode="json")),
    )


@router.put("/{group_id}", summary="编辑商品分组")
async def update_group(
    group_id: int, body: ProductGroupUpdate, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    group = await product_group_service.update_group(db, group_id, body)
    if not group:
        return JSONResponse(status_code=404, content=err(GROUP_NOT_FOUND, "Group not found"))
    return JSONResponse(content=ok(ProductGroupResponse.model_validate(group).model_dump(mode="json")))


@router.delete("/{group_id}", summary="删除商品分组")
async def delete_group(group_id: int, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    deleted = await product_group_service.delete_group(db, group_id)
    if not deleted:
        return JSONResponse(status_code=404, content=err(GROUP_NOT_FOUND, "Group not found"))
    return JSONResponse(content=ok(None, "deleted"))


@router.post("/{group_id}/products", status_code=201, summary="添加商品到分组")
async def add_group_product(
    group_id: int, body: GroupItemCreate, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    group = await product_group_service.get_group(db, group_id)
    if not group:
        return JSONResponse(status_code=404, content=err(GROUP_NOT_FOUND, "Group not found"))
    spu = await spu_service.get_spu(db, body.spu_id)
    if not spu:
        return JSONResponse(status_code=404, content=err(SPU_NOT_FOUND, "Product not found"))
    item, error = await product_group_service.add_group_product(db, group_id, body)
    if error == "duplicate":
        return JSONResponse(
            status_code=400, content=err(DUPLICATE_GROUP_PRODUCT, "Product already in group")
        )
    return JSONResponse(
        status_code=201,
        content=ok(GroupItemResponse.model_validate(item).model_dump(mode="json")),
    )


@router.delete("/{group_id}/products/{spu_id}", summary="从分组移除商品")
async def remove_group_product(
    group_id: int, spu_id: int, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    removed = await product_group_service.remove_group_product(db, group_id, spu_id)
    if not removed:
        return JSONResponse(status_code=404, content=err(SPU_NOT_FOUND, "Product not in group"))
    return JSONResponse(content=ok(None, "removed"))


@router.get("/{group_id}/products", summary="分组商品列表(Admin)")
async def list_group_products(group_id: int, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    group = await product_group_service.get_group(db, group_id)
    if not group:
        return JSONResponse(status_code=404, content=err(GROUP_NOT_FOUND, "Group not found"))
    items = await product_group_service.list_group_items(db, group_id)
    return JSONResponse(
        content=ok([GroupItemResponse.model_validate(i).model_dump(mode="json") for i in items])
    )

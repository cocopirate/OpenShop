"""Admin API routes for Category management."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import (
    CATEGORY_HAS_PRODUCTS,
    CATEGORY_LEVEL_EXCEEDED,
    CATEGORY_NOT_FOUND,
    err,
    ok,
)
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.services import category_service

router = APIRouter()


@router.get("/tree", summary="获取分类树")
async def get_category_tree(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    categories = await category_service.list_all_categories(db)
    tree = await category_service.build_category_tree(categories)
    return JSONResponse(content=ok([node.model_dump(mode="json") for node in tree]))


@router.post("", status_code=201, summary="创建分类")
async def create_category(body: CategoryCreate, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    result = await category_service.create_category(db, body)
    category, error = result
    if error == "parent_not_found":
        return JSONResponse(status_code=404, content=err(CATEGORY_NOT_FOUND, "Parent category not found"))
    if error == "level_exceeded":
        return JSONResponse(
            status_code=400, content=err(CATEGORY_LEVEL_EXCEEDED, "Category nesting exceeds max level (3)")
        )
    return JSONResponse(
        status_code=201,
        content=ok(CategoryResponse.model_validate(category).model_dump(mode="json")),
    )


@router.put("/{category_id}", summary="编辑分类")
async def update_category(
    category_id: int, body: CategoryUpdate, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    category = await category_service.update_category(db, category_id, body)
    if not category:
        return JSONResponse(status_code=404, content=err(CATEGORY_NOT_FOUND, "Category not found"))
    return JSONResponse(content=ok(CategoryResponse.model_validate(category).model_dump(mode="json")))


@router.delete("/{category_id}", summary="删除分类")
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    deleted, error = await category_service.delete_category(db, category_id)
    if error == "not_found":
        return JSONResponse(status_code=404, content=err(CATEGORY_NOT_FOUND, "Category not found"))
    if error == "has_products":
        return JSONResponse(
            status_code=400, content=err(CATEGORY_HAS_PRODUCTS, "Category has associated products")
        )
    return JSONResponse(content=ok(None, "deleted"))

"""Admin API routes for Attribute management."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ATTRIBUTE_NOT_FOUND, CATEGORY_NOT_FOUND, err, ok
from app.schemas.attribute import AttributeCreate, AttributeResponse, CategoryAttributeCreate, CategoryAttributeResponse
from app.services import attribute_service, category_service

router = APIRouter()


@router.post("", status_code=201, summary="创建属性")
async def create_attribute(body: AttributeCreate, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    attr = await attribute_service.create_attribute(db, body)
    return JSONResponse(
        status_code=201,
        content=ok(AttributeResponse.model_validate(attr).model_dump(mode="json")),
    )


@router.get("", summary="属性列表")
async def list_attributes(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    attrs = await attribute_service.list_attributes(db)
    return JSONResponse(content=ok([AttributeResponse.model_validate(a).model_dump(mode="json") for a in attrs]))


@router.post("/categories/{category_id}", status_code=201, summary="绑定属性到分类")
async def bind_category_attribute(
    category_id: int, body: CategoryAttributeCreate, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    category = await category_service.get_category(db, category_id)
    if not category:
        return JSONResponse(status_code=404, content=err(CATEGORY_NOT_FOUND, "Category not found"))
    binding = await attribute_service.bind_category_attribute(db, category_id, body)
    return JSONResponse(
        status_code=201,
        content=ok(CategoryAttributeResponse.model_validate(binding).model_dump(mode="json")),
    )

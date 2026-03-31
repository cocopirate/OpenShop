"""Admin BFF routes – aggregates product-service admin APIs for admin dashboard."""
from __future__ import annotations

from typing import Optional

import httpx
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.response import err

router = APIRouter()

_PRODUCT_BASE = settings.PRODUCT_SERVICE_URL + "/api/v1"


async def _forward(method: str, url: str, request: Request, **kwargs) -> JSONResponse:
    """Forward a request to an upstream service and relay the response."""
    hop_by_hop = {"host", "connection", "keep-alive", "transfer-encoding", "te", "trailer", "upgrade"}
    headers = {k: v for k, v in request.headers.items() if k.lower() not in hop_by_hop}
    body = await request.body()
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.request(method, url, headers=headers, content=body, **kwargs)
        except httpx.ConnectError:
            return JSONResponse(status_code=503, content=err(50301, "Upstream unavailable"))
        except httpx.TimeoutException:
            return JSONResponse(status_code=504, content=err(50401, "Upstream timeout"))
    return JSONResponse(status_code=resp.status_code, content=resp.json())


# --------------------------------------------------------------------------- #
# Product (SPU) admin routes                                                    #
# --------------------------------------------------------------------------- #


@router.post("/products", status_code=201, summary="创建商品")
async def create_product(request: Request) -> JSONResponse:
    return await _forward("POST", f"{_PRODUCT_BASE}/admin/products", request)


@router.get("/products", summary="商品列表")
async def list_products(
    request: Request,
    category_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> JSONResponse:
    params: dict = {"page": page, "size": size}
    if category_id is not None:
        params["category_id"] = category_id
    return await _forward("GET", f"{_PRODUCT_BASE}/admin/products", request, params=params)


@router.get("/products/{product_id}", summary="商品详情")
async def get_product(product_id: int, request: Request) -> JSONResponse:
    return await _forward("GET", f"{_PRODUCT_BASE}/admin/products/{product_id}", request)


@router.put("/products/{product_id}", summary="编辑商品")
async def update_product(product_id: int, request: Request) -> JSONResponse:
    return await _forward("PUT", f"{_PRODUCT_BASE}/admin/products/{product_id}", request)


@router.post("/products/{product_id}/publish", summary="商品上架")
async def publish_product(product_id: int, request: Request) -> JSONResponse:
    return await _forward("POST", f"{_PRODUCT_BASE}/admin/products/{product_id}/publish", request)


@router.post("/products/{product_id}/unpublish", summary="商品下架")
async def unpublish_product(product_id: int, request: Request) -> JSONResponse:
    return await _forward("POST", f"{_PRODUCT_BASE}/admin/products/{product_id}/unpublish", request)


# --------------------------------------------------------------------------- #
# SKU admin routes                                                              #
# --------------------------------------------------------------------------- #


@router.post("/skus/batch", status_code=201, summary="批量创建SKU")
async def batch_create_skus(request: Request) -> JSONResponse:
    return await _forward("POST", f"{_PRODUCT_BASE}/admin/skus/batch", request)


@router.put("/skus/{sku_id}", summary="编辑SKU")
async def update_sku(sku_id: int, request: Request) -> JSONResponse:
    return await _forward("PUT", f"{_PRODUCT_BASE}/admin/skus/{sku_id}", request)


@router.delete("/skus/{sku_id}", summary="删除SKU")
async def delete_sku(sku_id: int, request: Request) -> JSONResponse:
    return await _forward("DELETE", f"{_PRODUCT_BASE}/admin/skus/{sku_id}", request)


# --------------------------------------------------------------------------- #
# Category admin routes                                                         #
# --------------------------------------------------------------------------- #


@router.get("/categories/tree", summary="分类树")
async def get_category_tree(request: Request) -> JSONResponse:
    return await _forward("GET", f"{_PRODUCT_BASE}/admin/categories/tree", request)


@router.post("/categories", status_code=201, summary="创建分类")
async def create_category(request: Request) -> JSONResponse:
    return await _forward("POST", f"{_PRODUCT_BASE}/admin/categories", request)


@router.put("/categories/{category_id}", summary="编辑分类")
async def update_category(category_id: int, request: Request) -> JSONResponse:
    return await _forward("PUT", f"{_PRODUCT_BASE}/admin/categories/{category_id}", request)


@router.delete("/categories/{category_id}", summary="删除分类")
async def delete_category(category_id: int, request: Request) -> JSONResponse:
    return await _forward("DELETE", f"{_PRODUCT_BASE}/admin/categories/{category_id}", request)


# --------------------------------------------------------------------------- #
# Attribute admin routes                                                        #
# --------------------------------------------------------------------------- #


@router.post("/attributes", status_code=201, summary="创建属性")
async def create_attribute(request: Request) -> JSONResponse:
    return await _forward("POST", f"{_PRODUCT_BASE}/admin/attributes", request)


@router.get("/attributes", summary="属性列表")
async def list_attributes(request: Request) -> JSONResponse:
    return await _forward("GET", f"{_PRODUCT_BASE}/admin/attributes", request)


@router.post("/categories/{category_id}/attributes", status_code=201, summary="绑定属性到分类")
async def bind_category_attribute(category_id: int, request: Request) -> JSONResponse:
    return await _forward("POST", f"{_PRODUCT_BASE}/admin/attributes/categories/{category_id}", request)


# --------------------------------------------------------------------------- #
# Product Group admin routes                                                    #
# --------------------------------------------------------------------------- #


@router.post("/groups", status_code=201, summary="创建商品分组")
async def create_group(request: Request) -> JSONResponse:
    return await _forward("POST", f"{_PRODUCT_BASE}/admin/groups", request)


@router.put("/groups/{group_id}", summary="编辑商品分组")
async def update_group(group_id: int, request: Request) -> JSONResponse:
    return await _forward("PUT", f"{_PRODUCT_BASE}/admin/groups/{group_id}", request)


@router.delete("/groups/{group_id}", summary="删除商品分组")
async def delete_group(group_id: int, request: Request) -> JSONResponse:
    return await _forward("DELETE", f"{_PRODUCT_BASE}/admin/groups/{group_id}", request)


@router.post("/groups/{group_id}/products", status_code=201, summary="添加商品到分组")
async def add_group_product(group_id: int, request: Request) -> JSONResponse:
    return await _forward("POST", f"{_PRODUCT_BASE}/admin/groups/{group_id}/products", request)


@router.delete("/groups/{group_id}/products/{spu_id}", summary="从分组移除商品")
async def remove_group_product(group_id: int, spu_id: int, request: Request) -> JSONResponse:
    return await _forward("DELETE", f"{_PRODUCT_BASE}/admin/groups/{group_id}/products/{spu_id}", request)


@router.get("/groups/{group_id}/products", summary="分组商品列表")
async def list_group_products(group_id: int, request: Request) -> JSONResponse:
    return await _forward("GET", f"{_PRODUCT_BASE}/admin/groups/{group_id}/products", request)
